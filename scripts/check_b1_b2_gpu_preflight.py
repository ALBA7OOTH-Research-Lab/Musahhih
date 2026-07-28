"""Execute-check the frozen B1/B2 P100 runtime before private-input access."""

from __future__ import annotations

import importlib
import json
import os

from scripts.bootstrap_b1_b2_p100_runtime import (
    P100BootstrapError,
    require_proven_p100_stack,
)
from scripts.run_prompt_baseline import (
    RunSafetyError,
    require_single_p100_runtime,
)


def main() -> None:
    os.environ["UNSLOTH_COMPILE_DISABLE"] = "1"
    try:
        metadata = require_single_p100_runtime()
        import torch

        stack = require_proven_p100_stack(torch)
        for package in ("bitsandbytes", "unsloth"):
            importlib.import_module(package)
    except (ImportError, OSError, P100BootstrapError, RunSafetyError) as error:
        raise SystemExit(f"ERROR: {error}") from error
    print(
        json.dumps(
            {
                "stage": "b1_b2_gpu_preflight",
                "passed": True,
                "inference_imports_passed": True,
                "proven_stack": stack,
                **metadata,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
