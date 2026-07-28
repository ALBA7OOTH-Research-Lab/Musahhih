"""Restore and validate the already proven P100 stack in fresh processes."""

from __future__ import annotations

import json
import os
import subprocess
import sys


def run_restored_preflight(
    *,
    run_command=subprocess.run,
    executable: str = sys.executable,
    base_environment: dict[str, str] | None = None,
) -> dict:
    environment = dict(os.environ if base_environment is None else base_environment)
    environment["UNSLOTH_COMPILE_DISABLE"] = "1"
    commands = (
        [executable, "-m", "scripts.bootstrap_b1_b2_p100_runtime"],
        [executable, "-m", "scripts.check_b1_b2_gpu_preflight"],
    )
    for command in commands:
        run_command(command, check=True, env=environment)
    return {
        "stage": "b1_b2_restored_p100_preflight",
        "passed": True,
        "fresh_processes": True,
        "unsloth_compile_disabled": True,
        "private_input_accessed": False,
        "model_loaded": False,
    }


def main() -> None:
    print(json.dumps(run_restored_preflight(), sort_keys=True))


if __name__ == "__main__":
    main()
