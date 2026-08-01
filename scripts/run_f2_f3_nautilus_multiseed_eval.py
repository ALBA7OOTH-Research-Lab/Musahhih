#!/usr/bin/env python3
"""Run one timeout-safe paired-seed Nahw evaluation after an exact issue #171 GO."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import time

from scripts.f1_eval_utils import (
    BOOTSTRAP_SAMPLES,
    EXPECTED_TEST_RECORDS,
    EXPECTED_TEST_SHA256,
    load_and_validate_nahw_records,
    paired_comparison,
    sha256_file,
)
from scripts.f2_f3_multiseed_eval_utils import (
    EVALUATION_CONFIRMATION,
    TEST_FILENAME,
    validate_activation,
    validate_training_pair,
)
from scripts.f2_f3_eval_repair_utils import (
    COMMIT_PATTERN,
    SOURCE_ATTEMPT_ID,
    SOURCE_EVALUATION_COMMIT,
    validate_interrupted_source_identity,
    validate_repair_activation,
)
from scripts.f2_f3_nautilus_utils import a100_preflight, arm_order
from scripts.nahw_baseline_utils import parse_model_response, summarize_predictions
from scripts.run_f2_f3_final_eval import (
    AdapterGenerator,
    KernelTimeBudget,
    TimeBudgetExhausted,
    _fsync_path,
    _fsync_stream,
    _generate_arm,
    _read_prediction_rows,
    _release_generator,
    _validate_prediction_prefix,
    _write_json_atomic,
)
from scripts.run_f2_f3_nautilus_pair import actual_commit, runtime_summary


SAFE_STOP_ELAPSED_SECONDS = 64_800
PROGRESS_SCHEMA_VERSION = 1
REPAIR_BATCH_SIZE = 16


class MultiSeedRunError(RuntimeError):
    """Raised when private evaluation state violates the frozen contract."""


def validate_test_staging(input_root: Path) -> dict:
    path = Path(input_root) / "staging_manifest.json"
    try:
        observed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MultiSeedRunError("cannot read test staging manifest") from error
    expected = {
        "status": "complete",
        "filename": TEST_FILENAME,
        "records": EXPECTED_TEST_RECORDS,
        "sha256": EXPECTED_TEST_SHA256,
        "contains_corpus_text": False,
    }
    if observed != expected:
        raise MultiSeedRunError("test staging manifest contract mismatch")
    return observed


def _prediction_paths(attempt_root: Path) -> dict[str, Path]:
    return {
        arm: attempt_root / f"{arm.lower()}_predictions.jsonl"
        for arm in ("F2-P1", "F3-P1")
    }


def _progress_payload(
    *,
    activation: dict,
    completed: dict[str, int],
    prediction_paths: dict[str, Path],
    runtime: dict,
    adapter_meta: dict[str, dict],
    budget: KernelTimeBudget,
    status: str,
) -> dict:
    return {
        "schema_version": PROGRESS_SCHEMA_VERSION,
        "status": status,
        "seed": activation["seed"],
        "approved_commit": activation["approved_commit"],
        "attempt_id": activation["attempt_id"],
        "completed_records": dict(completed),
        "prediction_sha256": {
            arm: sha256_file(path) if path.is_file() else None
            for arm, path in prediction_paths.items()
        },
        "runtime": runtime,
        "adapters": adapter_meta,
        "test_sha256": EXPECTED_TEST_SHA256,
        "elapsed_seconds": budget.elapsed_seconds(),
        "resume_source": activation.get("resume_source"),
        "contains_corpus_text": False,
    }


def _load_resume(
    resume_root: Path | None,
    *,
    records: list[dict],
    seed: int,
    approved_commit: str,
    adapter_meta: dict[str, dict],
    resume_source_commit: str | None = None,
    interrupted_source: dict | None = None,
) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    empty = {"F2-P1": [], "F3-P1": []}
    if resume_root is None:
        return empty, {}
    root = Path(resume_root).resolve()
    progress_path = root / "progress.json"
    try:
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MultiSeedRunError("invalid private resume metadata") from error
    source_commit = resume_source_commit or approved_commit
    if interrupted_source is None:
        summary_path = root / "public_summary.json"
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise MultiSeedRunError("invalid private resume summary") from error
        if (
            summary.get("run_status")
            not in ("incomplete_time_budget", "incomplete_resource_guard")
            or summary.get("seed") != seed
            or summary.get("approved_commit") != source_commit
            or summary.get("metrics_reported") is not False
        ):
            raise MultiSeedRunError("resume summary contract mismatch")
    else:
        if (
            interrupted_source.get("seed") != seed
            or interrupted_source.get("source_attempt_id") != root.name
            or interrupted_source.get("source_commit") != source_commit
            or progress.get("status") != "running"
            or progress.get("attempt_id") != root.name
            or progress.get("completed_records")
            != interrupted_source.get("recorded_counts")
        ):
            raise MultiSeedRunError("interrupted resume source contract mismatch")
    if (
        progress.get("schema_version") != PROGRESS_SCHEMA_VERSION
        or progress.get("seed") != seed
        or progress.get("approved_commit") != source_commit
        or progress.get("adapters") != adapter_meta
        or progress.get("test_sha256") != EXPECTED_TEST_SHA256
        or progress.get("contains_corpus_text") is not False
    ):
        raise MultiSeedRunError("resume progress contract mismatch")

    prefixes: dict[str, list[dict]] = {}
    runtimes = progress.get("runtime")
    if not isinstance(runtimes, dict):
        raise MultiSeedRunError("resume runtime metadata is invalid")
    for arm in ("F2-P1", "F3-P1"):
        path = root / f"{arm.lower()}_predictions.jsonl"
        rows = _read_prediction_rows(path, arm)
        _validate_prediction_prefix(rows, records, arm=arm)
        recorded_count = progress.get("completed_records", {}).get(arm)
        if not isinstance(recorded_count, int) or len(rows) not in (
            recorded_count,
            recorded_count + 1,
        ):
            raise MultiSeedRunError(f"{arm} resume count mismatch")
        expected_hash = progress.get("prediction_sha256", {}).get(arm)
        if rows:
            observed_hash = sha256_file(path)
            if len(rows) == recorded_count and expected_hash != observed_hash:
                raise MultiSeedRunError(f"{arm} resume hash mismatch")
            if len(rows) == recorded_count + 1 and expected_hash == observed_hash:
                raise MultiSeedRunError(f"{arm} orphan-row evidence is inconsistent")
        elif expected_hash is not None or path.exists():
            raise MultiSeedRunError(f"{arm} empty resume mismatch")
        prefixes[arm] = rows
    order = arm_order(seed)
    if len(prefixes[order[0]]) < EXPECTED_TEST_RECORDS and prefixes[order[1]]:
        raise MultiSeedRunError("resume contains second-arm rows too early")
    return prefixes, runtimes


def _copy_resume_predictions(
    resume_root: Path | None,
    prefixes: dict[str, list[dict]],
    destination: dict[str, Path],
) -> None:
    if resume_root is None:
        return
    for arm, rows in prefixes.items():
        if rows:
            shutil.copyfile(
                Path(resume_root) / f"{arm.lower()}_predictions.jsonl",
                destination[arm],
            )
            _fsync_path(destination[arm])


def _failure_digest(error: BaseException) -> str:
    return hashlib.sha256(
        str(error).encode("utf-8", errors="replace")
    ).hexdigest()


def _generate_arm_batched(
    *,
    arm: str,
    adapter: Path,
    records: list[dict],
    predictions_path: Path,
    prefix_rows: list[dict],
    budget: KernelTimeBudget,
    progress_callback,
    batch_size: int,
    generator_factory=AdapterGenerator,
) -> tuple[list[dict], dict]:
    """Generate fixed-size batches while retaining per-row durable commits."""

    if batch_size < 2:
        raise MultiSeedRunError("repaired batch size must be at least two")
    rows = list(prefix_rows)
    mode = "a" if predictions_path.is_file() else "x"
    generator = generator_factory(adapter)
    try:
        with predictions_path.open(mode, encoding="utf-8", newline="\n") as stream:
            while len(rows) < len(records):
                budget.require_next_record_budget()
                batch = records[len(rows) : len(rows) + batch_size]
                raw_outputs = generator.generate_batch(
                    [record["prompt"] for record in batch]
                )
                if len(raw_outputs) != len(batch):
                    raise MultiSeedRunError("batched response count mismatch")
                for record, raw in zip(batch, raw_outputs, strict=True):
                    parsed, warnings = parse_model_response(raw)
                    row = {
                        "record_id": record["id"],
                        "passage_id": record["passage_id"],
                        "source": record["source"],
                        "split": record["split"],
                        "passage": record["passage"],
                        "erroneous_word": record["error"],
                        "gold_correction": record["gold_correction"],
                        "full_prompt": record["prompt"],
                        "raw_model_response": raw,
                        "parsed_correction": parsed,
                        "exact_match": parsed == record["gold_correction"],
                        "parsing_warnings": warnings,
                    }
                    stream.write(
                        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                    )
                    _fsync_stream(stream)
                    rows.append(row)
                    progress_callback(len(rows), generator.runtime)
        if len(rows) != EXPECTED_TEST_RECORDS:
            raise MultiSeedRunError(f"{arm} did not complete exactly 511 records")
        return rows, generator.runtime
    finally:
        _release_generator(generator)


def execute(
    *,
    activation: dict,
    records: list[dict],
    adapter_meta: dict[str, dict],
    output_root: Path,
    resume_root: Path | None,
    kernel_start_epoch_seconds: float,
    resume_source_commit: str | None = None,
    interrupted_source: dict | None = None,
    batch_size: int = 1,
) -> dict:
    seed = activation["seed"]
    seed_root = Path(output_root) / f"seed-{seed}"
    budget = KernelTimeBudget(
        kernel_start_epoch_seconds,
        safe_stop_elapsed_seconds=SAFE_STOP_ELAPSED_SECONDS,
    )
    public_adapter_meta = _public_adapter_meta(adapter_meta)
    prefixes, runtimes = _load_resume(
        resume_root,
        records=records,
        seed=seed,
        approved_commit=activation["approved_commit"],
        adapter_meta=public_adapter_meta,
        resume_source_commit=resume_source_commit,
        interrupted_source=interrupted_source,
    )
    attempt_root = seed_root / "attempts" / activation["attempt_id"]
    attempt_root.mkdir(parents=True, exist_ok=False)
    paths = _prediction_paths(attempt_root)
    progress_path = attempt_root / "progress.json"
    summary_path = attempt_root / "public_summary.json"
    _copy_resume_predictions(resume_root, prefixes, paths)
    completed = {arm: len(rows) for arm, rows in prefixes.items()}

    def persist(status: str) -> None:
        payload = _progress_payload(
            activation=activation,
            completed=completed,
            prediction_paths=paths,
            runtime=runtimes,
            adapter_meta=public_adapter_meta,
            budget=budget,
            status=status,
        )
        temporary = progress_path.with_suffix(".json.tmp")
        _write_json_atomic(temporary, payload)
        os.replace(temporary, progress_path)

    persist("running")
    rows_by_arm: dict[str, list[dict]] = {}
    try:
        for arm in arm_order(seed):
            if len(prefixes[arm]) == EXPECTED_TEST_RECORDS:
                rows_by_arm[arm] = prefixes[arm]
                continue

            def on_progress(count: int, runtime: dict, *, current=arm) -> None:
                completed[current] = count
                runtimes[current] = runtime
                persist("running")

            generation = _generate_arm if batch_size == 1 else _generate_arm_batched
            generation_args = {
                "arm": arm,
                "adapter": adapter_meta[arm]["adapter_path"],
                "records": records,
                "predictions_path": paths[arm],
                "prefix_rows": prefixes[arm],
                "budget": budget,
                "progress_callback": on_progress,
                "generator_factory": lambda adapter: AdapterGenerator(
                    adapter, required_gpu="A100"
                ),
            }
            if batch_size != 1:
                generation_args["batch_size"] = batch_size
            rows, runtime = generation(**generation_args)
            rows_by_arm[arm] = rows
            runtimes[arm] = runtime
            completed[arm] = len(rows)
            persist("running")

        comparison = paired_comparison(
            rows_by_arm["F2-P1"],
            rows_by_arm["F3-P1"],
            bootstrap_samples=BOOTSTRAP_SAMPLES,
            seed=seed,
        )
        arms = {}
        for arm, rows in rows_by_arm.items():
            counts = summarize_predictions(rows)
            warning_counts = Counter(
                warning for row in rows for warning in row["parsing_warnings"]
            )
            arms[arm] = {
                "records": counts["number_of_records"],
                "correct": counts["number_correct"],
                "accuracy": counts["exact_match_accuracy"],
                "invalid_or_empty_count": counts["invalid_or_empty_count"],
                "suspicious_output_count": counts["suspicious_output_count"],
                "multi_token_count": counts["multi_token_count"],
                "warning_counts": dict(sorted(warning_counts.items())),
                "predictions_sha256": sha256_file(paths[arm]),
            }
        persist("complete")
        summary = {
            "schema_version": 1,
            "run_status": "complete",
            "seed": seed,
            "arm_order": list(arm_order(seed)),
            "created_utc": datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "approved_commit": activation["approved_commit"],
            "approval_reference": activation["approval_reference"],
            "attempt_id": activation["attempt_id"],
            "training_commit": next(iter(public_adapter_meta.values()))[
                "training_commit"
            ],
            "records": EXPECTED_TEST_RECORDS,
            "test_sha256": EXPECTED_TEST_SHA256,
            "adapters": public_adapter_meta,
            "arms": arms,
            "comparison": {
                "f3_minus_f2": comparison[
                    "accuracy_difference_adapter_minus_baseline"
                ],
                "f2_wrong_f3_right": comparison[
                    "baseline_wrong_adapter_right"
                ],
                "f2_right_f3_wrong": comparison[
                    "baseline_right_adapter_wrong"
                ],
                "mcnemar_two_sided_exact_p_value": comparison[
                    "mcnemar_two_sided_exact_p_value"
                ],
                "paired_bootstrap_95_percentile_ci": comparison[
                    "paired_bootstrap_95_percentile_ci"
                ],
                "bootstrap_samples": BOOTSTRAP_SAMPLES,
                "bootstrap_seed": seed,
            },
            "runtime": runtimes,
            "contains_corpus_text": False,
            "development_values_exposed": False,
            "training_executed": False,
            "qalb_test_used": False,
            "prompt_or_parser_changed": False,
            "automatic_retry": False,
            "batch_size": batch_size,
            "batch_equivalence_canary_required": batch_size > 1,
        }
        _write_json_atomic(summary_path, summary)
        return summary
    except TimeBudgetExhausted:
        persist("incomplete_time_budget")
        summary = {
            "schema_version": 1,
            "run_status": "incomplete_time_budget",
            "seed": seed,
            "approved_commit": activation["approved_commit"],
            "attempt_id": activation["attempt_id"],
            "completed_records": completed,
            "elapsed_seconds": budget.elapsed_seconds(),
            "safe_stop_elapsed_seconds": SAFE_STOP_ELAPSED_SECONDS,
            "metrics_reported": False,
            "resume_requires_fresh_authorization": True,
            "batch_size": batch_size,
            "resume_source": activation.get("resume_source"),
            "contains_corpus_text": False,
        }
        _write_json_atomic(summary_path, summary)
        return summary
    except BaseException as error:
        failure = {
            "schema_version": 1,
            "run_status": "failed",
            "seed": seed,
            "approved_commit": activation["approved_commit"],
            "attempt_id": activation["attempt_id"],
            "completed_records": completed,
            "error_type": type(error).__name__,
            "error_message_sha256": _failure_digest(error),
            "metrics_reported": False,
            "resume_requires_fresh_authorization": True,
            "batch_size": batch_size,
            "resume_source": activation.get("resume_source"),
            "contains_corpus_text": False,
        }
        _write_json_atomic(summary_path, failure)
        raise


def _public_adapter_meta(validated: dict[str, dict]) -> dict[str, dict]:
    return {
        arm: {key: value for key, value in meta.items() if key != "adapter_path"}
        for arm, meta in validated.items()
    }


def _require_private_absolute_path(path: Path, label: str) -> Path:
    resolved = Path(path).resolve()
    if not resolved.is_absolute() or not str(resolved).replace("\\", "/").startswith(
        "/private/"
    ):
        raise MultiSeedRunError(f"{label} must be under /private")
    return resolved


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--training-root", required=True, type=Path)
    parser.add_argument("--test-input-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--resume-root", type=Path)
    parser.add_argument("--kernel-start-epoch-seconds", required=True, type=float)
    parser.add_argument("--approved-commit", required=True)
    parser.add_argument("--approval-reference", required=True)
    parser.add_argument("--confirmation", required=True)
    parser.add_argument("--repair-continuation", action="store_true")
    parser.add_argument("--resume-source-attempt-id")
    parser.add_argument("--resume-source-commit")
    parser.add_argument("--batch-size", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commit = actual_commit()
    interrupted_source = None
    if args.repair_continuation:
        activation = validate_repair_activation(
            stage="continuation",
            seed=args.seed,
            approved_commit=args.approved_commit,
            actual_commit=commit,
            approval_reference=args.approval_reference,
            confirmation=args.confirmation,
        )
        source_attempt_id = args.resume_source_attempt_id or ""
        source_commit = args.resume_source_commit or ""
        if (
            source_attempt_id == SOURCE_ATTEMPT_ID
            and source_commit == SOURCE_EVALUATION_COMMIT
        ):
            interrupted_source = validate_interrupted_source_identity(
                seed=args.seed,
                source_attempt_id=source_attempt_id,
                source_commit=source_commit,
            )
            activation["resume_source"] = interrupted_source
        else:
            if (
                not source_attempt_id.isdigit()
                or source_attempt_id.startswith("0")
                or not COMMIT_PATTERN.fullmatch(source_commit)
            ):
                raise MultiSeedRunError("repair handoff source identity is invalid")
            activation["resume_source"] = {
                "seed": args.seed,
                "source_attempt_id": source_attempt_id,
                "source_commit": source_commit,
                "terminal_state": "metric_free_repair_handoff",
                "contains_corpus_text": False,
            }
        if args.batch_size != REPAIR_BATCH_SIZE or args.resume_root is None:
            raise MultiSeedRunError(
                "repair continuation requires the frozen batch and resume source"
            )
    else:
        activation = validate_activation(
            stage="paired-evaluation",
            seed=args.seed,
            approved_commit=args.approved_commit,
            actual_commit=commit,
            approval_reference=args.approval_reference,
            confirmation=args.confirmation,
        )
        if (
            args.batch_size != 1
            or args.resume_source_attempt_id is not None
            or args.resume_source_commit is not None
        ):
            raise MultiSeedRunError("original evaluation cannot use repair arguments")

    os.environ["UNSLOTH_COMPILE_DISABLE"] = "1"
    import torch

    gpu = a100_preflight(torch)
    runtime_summary(torch, gpu)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False

    training_root = _require_private_absolute_path(args.training_root, "training root")
    test_root = _require_private_absolute_path(args.test_input_root, "test input root")
    output_root = _require_private_absolute_path(args.output_root, "output root")
    resume_root = (
        _require_private_absolute_path(args.resume_root, "resume root")
        if args.resume_root is not None
        else None
    )
    if resume_root is not None:
        try:
            resume_root.relative_to(output_root)
        except ValueError as error:
            raise MultiSeedRunError("resume root must stay under output root") from error
    if args.repair_continuation and (
        resume_root is None
        or resume_root.name != args.resume_source_attempt_id
        or resume_root.parent.parent.name != f"seed-{args.seed}"
    ):
        raise MultiSeedRunError("repair resume path does not match frozen source")

    seed_root = training_root / f"seed-{args.seed}"
    validated = validate_training_pair(seed_root, args.seed)
    adapter_meta = _public_adapter_meta(validated)
    validate_test_staging(test_root)
    records = load_and_validate_nahw_records(test_root / TEST_FILENAME)
    summary = execute(
        activation=activation,
        records=records,
        adapter_meta={
            arm: {**adapter_meta[arm], "adapter_path": validated[arm]["adapter_path"]}
            for arm in adapter_meta
        },
        output_root=output_root,
        resume_root=resume_root,
        kernel_start_epoch_seconds=args.kernel_start_epoch_seconds,
        resume_source_commit=args.resume_source_commit,
        interrupted_source=interrupted_source,
        batch_size=args.batch_size,
    )
    print(
        json.dumps(
            {
                "run_status": summary["run_status"],
                "seed": args.seed,
                "completed_records": (
                    {arm: EXPECTED_TEST_RECORDS for arm in ("F2-P1", "F3-P1")}
                    if summary["run_status"] == "complete"
                    else summary.get("completed_records", {})
                ),
                "metrics_printed": False,
                "contains_corpus_text": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
