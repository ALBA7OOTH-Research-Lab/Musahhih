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
from scripts.f2_f3_nautilus_utils import a100_preflight, arm_order
from scripts.nahw_baseline_utils import summarize_predictions
from scripts.run_f2_f3_final_eval import (
    AdapterGenerator,
    KernelTimeBudget,
    TimeBudgetExhausted,
    _fsync_path,
    _generate_arm,
    _read_prediction_rows,
    _validate_prediction_prefix,
    _write_json_atomic,
)
from scripts.run_f2_f3_nautilus_pair import actual_commit, runtime_summary


SAFE_STOP_ELAPSED_SECONDS = 64_800
PROGRESS_SCHEMA_VERSION = 1


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
        "contains_corpus_text": False,
    }


def _load_resume(
    resume_root: Path | None,
    *,
    records: list[dict],
    seed: int,
    approved_commit: str,
    adapter_meta: dict[str, dict],
) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    empty = {"F2-P1": [], "F3-P1": []}
    if resume_root is None:
        return empty, {}
    root = Path(resume_root).resolve()
    summary_path = root / "public_summary.json"
    progress_path = root / "progress.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise MultiSeedRunError("invalid private resume metadata") from error
    if (
        summary.get("run_status") != "incomplete_time_budget"
        or summary.get("seed") != seed
        or summary.get("approved_commit") != approved_commit
        or summary.get("metrics_reported") is not False
        or progress.get("schema_version") != PROGRESS_SCHEMA_VERSION
        or progress.get("seed") != seed
        or progress.get("approved_commit") != approved_commit
        or progress.get("adapters") != adapter_meta
        or progress.get("test_sha256") != EXPECTED_TEST_SHA256
        or progress.get("contains_corpus_text") is not False
    ):
        raise MultiSeedRunError("resume metadata contract mismatch")

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


def execute(
    *,
    activation: dict,
    records: list[dict],
    adapter_meta: dict[str, dict],
    output_root: Path,
    resume_root: Path | None,
    kernel_start_epoch_seconds: float,
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

            rows, runtime = _generate_arm(
                arm=arm,
                adapter=adapter_meta[arm]["adapter_path"],
                records=records,
                predictions_path=paths[arm],
                prefix_rows=prefixes[arm],
                budget=budget,
                progress_callback=on_progress,
                generator_factory=lambda adapter: AdapterGenerator(
                    adapter, required_gpu="A100"
                ),
            )
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    commit = actual_commit()
    activation = validate_activation(
        stage="paired-evaluation",
        seed=args.seed,
        approved_commit=args.approved_commit,
        actual_commit=commit,
        approval_reference=args.approval_reference,
        confirmation=args.confirmation,
    )

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
