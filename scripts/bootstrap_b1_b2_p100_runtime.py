"""Restore the P100 stack already proven by Musahhih F2/F3 runs."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import subprocess
import sys


PYTORCH_INDEX = "https://download.pytorch.org/whl/cu124"
RESTORED_P100_STACK = {
    "torch": "2.6.0",
    "torchvision": "0.21.0",
    "numpy": "2.0.2",
    "xformers": "0.0.29.post3",
    "torchao": "0.16.0",
    "transformers": "4.56.2",
    "unsloth": "2026.7.3",
    # Unsloth 2026.7.3 requires unsloth_zoo>=2026.7.3; pin the minimum.
    "unsloth_zoo": "2026.7.3",
    "accelerate": "1.13.0",
    "peft": "0.19.1",
    "trl": "0.22.2",
    "datasets": "4.3.0",
    "bitsandbytes": "0.49.2",
}
REPORT_ONLY_PACKAGES = ("triton",)
HEAVY_PACKAGES = ("torch", "torchvision", "numpy")


class P100BootstrapError(RuntimeError):
    """Raised when the proven P100 runtime cannot be restored exactly."""


def _version(name: str, getter) -> str | None:
    try:
        return getter(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def installed_versions(getter=None) -> dict[str, str | None]:
    getter = getter or importlib.metadata.version
    return {
        name: _version(name, getter)
        for name in (*RESTORED_P100_STACK, *REPORT_ONLY_PACKAGES)
    }


def _base(version: str | None) -> str | None:
    return version.split("+", 1)[0] if isinstance(version, str) else None


def stack_report(versions: dict[str, str | None]) -> dict:
    mismatches = {}
    for name, expected in RESTORED_P100_STACK.items():
        observed = versions.get(name)
        comparable = _base(observed) if name in ("torch", "torchvision") else observed
        if comparable != expected:
            mismatches[name] = {"expected": expected, "installed": observed}
    return {
        "compatible": not mismatches,
        "installed": {name: versions.get(name) for name in RESTORED_P100_STACK},
        "mismatches": mismatches,
        "required": dict(RESTORED_P100_STACK),
    }


def require_proven_p100_stack(
    torch_module,
    *,
    getter=None,
) -> dict:
    versions = installed_versions(getter)
    report = stack_report(versions)
    if not report["compatible"]:
        raise P100BootstrapError("proven P100 package identities are unavailable")
    cuda_runtime = getattr(getattr(torch_module, "version", None), "cuda", None)
    if cuda_runtime != "12.4":
        raise P100BootstrapError("proven P100 runtime requires CUDA 12.4")
    return {
        **report,
        "cuda_runtime": cuda_runtime,
        "report_only_versions": {
            name: versions.get(name) for name in REPORT_ONLY_PACKAGES
        },
    }


def bootstrap_commands(versions: dict[str, str | None]) -> list[list[str]]:
    report = stack_report(versions)
    if report["compatible"]:
        return []
    commands = []
    if any(name in report["mismatches"] for name in ("torch", "torchvision")):
        commands.append(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--progress-bar",
                "off",
                "--upgrade",
                "torch==2.6.0",
                "torchvision==0.21.0",
                "--index-url",
                PYTORCH_INDEX,
            ]
        )
    if "numpy" in report["mismatches"]:
        commands.append(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--progress-bar",
                "off",
                "--upgrade",
                "numpy==2.0.2",
            ]
        )
    if any(name not in HEAVY_PACKAGES for name in report["mismatches"]):
        commands.extend(
            [
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--progress-bar",
                    "off",
                    "sentencepiece",
                    "protobuf",
                    "datasets==4.3.0",
                    "huggingface_hub>=0.34.0",
                    "hf_transfer",
                ],
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--progress-bar",
                    "off",
                    "--upgrade",
                    "--no-deps",
                    "xformers==0.0.29.post3",
                    "torchao==0.16.0",
                    "unsloth==2026.7.3",
                    "unsloth_zoo==2026.7.3",
                    "bitsandbytes==0.49.2",
                    "accelerate==1.13.0",
                    "peft==0.19.1",
                    "trl==0.22.2",
                ],
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--quiet",
                    "--progress-bar",
                    "off",
                    "--upgrade",
                    "transformers==4.56.2",
                ],
            ]
        )
    return commands


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def bootstrap(
    *,
    getter=None,
    run_command=subprocess.run,
) -> dict:
    before = installed_versions(getter)
    commands = bootstrap_commands(before)
    command_reports = []
    for command in commands:
        completed = run_command(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        command_reports.append(
            {
                "returncode": completed.returncode,
                "stdout_sha256": _sha256(completed.stdout),
                "stderr_sha256": _sha256(completed.stderr),
            }
        )
        if completed.returncode:
            raise P100BootstrapError("proven P100 package bootstrap failed")
    after = installed_versions(getter)
    final = stack_report(after)
    if not final["compatible"]:
        raise P100BootstrapError("proven P100 package identities did not validate")
    return {
        "stage": "b1_b2_proven_p100_bootstrap",
        "passed": True,
        "install_performed": bool(commands),
        "commands_executed": len(commands),
        "command_reports": command_reports,
        "stack": final,
        "report_only_versions": {
            name: after.get(name) for name in REPORT_ONLY_PACKAGES
        },
        "pytorch_index": PYTORCH_INDEX,
        "private_input_accessed": False,
        "model_loaded": False,
    }


def main() -> None:
    print(json.dumps(bootstrap(), sort_keys=True))


if __name__ == "__main__":
    main()
