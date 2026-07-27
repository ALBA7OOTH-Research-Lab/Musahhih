#!/usr/bin/env python3
"""Install and import-check the B1/B2 inference layer without model or data access."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


EXPECTED_BASE = {
    "torch": "2.10.0+cu128",
    "torchvision": "0.25.0+cu128",
    "numpy": "2.0.2",
    "cuda_runtime": "12.8",
}
DIRECT_REQUIREMENTS = (
    "unsloth[cu128-torch2100]==2026.7.2",
    "unsloth_zoo==2026.7.2",
    "bitsandbytes==0.49.2",
    "transformers==4.56.2",
    "trl==0.23.0",
)
CONSTRAINTS = (
    "torch==2.10.0",
    "torchvision==0.25.0",
    "numpy==2.0.2",
    "xformers==0.0.34",
)
REPORT_PACKAGES = (
    "torch",
    "torchvision",
    "numpy",
    "unsloth",
    "unsloth_zoo",
    "bitsandbytes",
    "transformers",
    "trl",
    "xformers",
    "accelerate",
    "peft",
)


def _version(name: str, version_getter=importlib.metadata.version) -> str | None:
    try:
        return version_getter(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def base_runtime_report(torch_module, *, version_getter=importlib.metadata.version) -> dict:
    """Verify the exact observed P100 base before any package installation."""

    versions = {
        name: _version(name, version_getter)
        for name in ("torch", "torchvision", "numpy")
    }
    cuda_available = bool(torch_module.cuda.is_available())
    device_count = int(torch_module.cuda.device_count()) if cuda_available else 0
    device_name = (
        str(torch_module.cuda.get_device_name(0))
        if cuda_available and device_count
        else None
    )
    cuda_runtime = getattr(getattr(torch_module, "version", None), "cuda", None)
    failures = []
    if versions != {
        name: EXPECTED_BASE[name] for name in ("torch", "torchvision", "numpy")
    }:
        failures.append("base_package_identity_mismatch")
    if cuda_runtime != EXPECTED_BASE["cuda_runtime"]:
        failures.append("cuda_runtime_mismatch")
    if not cuda_available:
        failures.append("cuda_unavailable")
    elif device_count != 1:
        failures.append("cuda_device_count_not_one")
    elif "P100" not in device_name.upper():
        failures.append("gpu_is_not_p100")
    return {
        "versions": versions,
        "cuda_available": cuda_available,
        "cuda_device_count": device_count,
        "device_name": device_name,
        "cuda_runtime": cuda_runtime,
        "failures": failures,
    }


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run_dependency_smoke(
    *,
    torch_module=None,
    version_getter=importlib.metadata.version,
    import_module=importlib.import_module,
    run_command=subprocess.run,
) -> dict:
    """Run a PyPI-only install and aggregate import smoke."""

    if torch_module is None:
        try:
            import torch as torch_module
        except (ImportError, OSError):
            return {
                "stage": "b1_b2_dependency_smoke",
                "probe_complete": True,
                "ready": False,
                "failures": ["pytorch_import_unavailable"],
                "install_attempted": False,
                "public_package_index_accessed": False,
                "private_input_accessed": False,
                "model_loaded": False,
            }

    before = base_runtime_report(torch_module, version_getter=version_getter)
    if before["failures"]:
        return {
            "stage": "b1_b2_dependency_smoke",
            "probe_complete": True,
            "ready": False,
            "failures": before["failures"],
            "install_attempted": False,
            "public_package_index_accessed": False,
            "base_before": before,
            "private_input_accessed": False,
            "model_loaded": False,
        }

    os.environ["UNSLOTH_COMPILE_DISABLE"] = "1"
    with tempfile.TemporaryDirectory(prefix="musahhih-b1-b2-") as temp_dir:
        constraint_path = Path(temp_dir) / "constraints.txt"
        constraint_path.write_text("\n".join(CONSTRAINTS) + "\n", encoding="utf-8")
        install_command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-input",
            "--index-url",
            "https://pypi.org/simple",
            "--constraint",
            str(constraint_path),
            *DIRECT_REQUIREMENTS,
        ]
        installed = run_command(
            install_command,
            capture_output=True,
            text=True,
            check=False,
        )

    failures = []
    if installed.returncode:
        failures.append("dependency_install_failed")

    imported = {}
    if not installed.returncode:
        for name in ("bitsandbytes", "unsloth"):
            try:
                module = import_module(name)
                imported[name] = True
                if name == "unsloth" and not hasattr(module, "FastModel"):
                    failures.append("unsloth_fastmodel_unavailable")
            except Exception:
                imported[name] = False
                failures.append(f"{name}_import_failed")

    checked = None
    if not installed.returncode and not failures:
        checked = run_command(
            [sys.executable, "-m", "pip", "check"],
            capture_output=True,
            text=True,
            check=False,
        )
        if checked.returncode:
            failures.append("pip_check_failed")

    after = base_runtime_report(torch_module, version_getter=version_getter)
    if after["failures"]:
        failures.append("base_runtime_changed")
    packages = {name: _version(name, version_getter) for name in REPORT_PACKAGES}
    return {
        "stage": "b1_b2_dependency_smoke",
        "probe_complete": True,
        "ready": not failures,
        "failures": failures,
        "install_attempted": True,
        "public_package_index_accessed": True,
        "install_returncode": installed.returncode,
        "install_stdout_sha256": _sha256_text(installed.stdout),
        "install_stderr_sha256": _sha256_text(installed.stderr),
        "pip_check_returncode": None if checked is None else checked.returncode,
        "imports": imported,
        "base_before": before,
        "base_after": after,
        "packages": packages,
        "index": "https://pypi.org/simple",
        "direct_requirements": list(DIRECT_REQUIREMENTS),
        "constraints": list(CONSTRAINTS),
        "private_input_accessed": False,
        "model_loaded": False,
    }


def main() -> None:
    print(json.dumps(run_dependency_smoke(), sort_keys=True))


if __name__ == "__main__":
    main()
