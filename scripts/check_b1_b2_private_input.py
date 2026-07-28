"""Validate the exact frozen B1/B2 input contract without printing corpus text."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.run_prompt_baseline import (
    FINAL_INPUT_SHA256,
    RunSafetyError,
    load_prompt_records,
    sha256_file,
    validate_private_path,
)


def validate(input_path: Path) -> dict:
    input_path = validate_private_path(input_path, label="input")
    try:
        digest = sha256_file(input_path)
    except OSError as error:
        raise RunSafetyError("unable to hash private input file") from error
    if digest != FINAL_INPUT_SHA256:
        raise RunSafetyError("private input SHA-256 does not match the frozen input")
    records = load_prompt_records(input_path)
    return {
        "input_sha256": digest,
        "passed": True,
        "record_count": len(records),
        "stage": "b1_b2_private_input_contract",
        "unique_record_ids": len({record.record_id for record in records})
        == len(records),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate(args.input)
    except RunSafetyError as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
