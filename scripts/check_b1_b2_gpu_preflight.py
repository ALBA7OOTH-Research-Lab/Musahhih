"""Check the frozen B1/B2 P100 runtime before any private-input access."""

from __future__ import annotations

import json

from scripts.run_prompt_baseline import (
    RunSafetyError,
    require_single_p100_runtime,
)


def main() -> None:
    try:
        metadata = require_single_p100_runtime()
    except RunSafetyError as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(
        json.dumps(
            {
                "stage": "b1_b2_gpu_preflight",
                "passed": True,
                **metadata,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
