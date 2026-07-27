#!/usr/bin/env python3
"""Report a Kaggle GPU/runtime without network, repository, model, or data access."""

from __future__ import annotations

import importlib.metadata
import json
import platform


PACKAGE_NAMES = (
    "torch",
    "torchvision",
    "transformers",
    "unsloth",
    "bitsandbytes",
    "xformers",
    "accelerate",
    "peft",
    "trl",
    "numpy",
)
REQUIRED_INFERENCE_PACKAGES = (
    "torch",
    "transformers",
    "unsloth",
    "bitsandbytes",
)


def installed_versions(version_getter=importlib.metadata.version) -> dict[str, str | None]:
    """Return package metadata only; importing inference packages is unnecessary."""

    versions: dict[str, str | None] = {}
    for name in PACKAGE_NAMES:
        try:
            versions[name] = version_getter(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def runtime_report(torch_module=None, *, version_getter=importlib.metadata.version) -> dict:
    """Build a corpus-text-free report of the preinstalled Kaggle runtime."""

    versions = installed_versions(version_getter)
    failures: list[str] = []
    if torch_module is None:
        try:
            import torch as torch_module
        except (ImportError, OSError):
            torch_module = None

    cuda_available = False
    device_count = 0
    device_name = None
    cuda_runtime = None
    if torch_module is None:
        failures.append("pytorch_import_unavailable")
    else:
        cuda_available = bool(torch_module.cuda.is_available())
        cuda_runtime = getattr(getattr(torch_module, "version", None), "cuda", None)
        if not cuda_available:
            failures.append("cuda_unavailable")
        else:
            device_count = int(torch_module.cuda.device_count())
            if device_count != 1:
                failures.append("cuda_device_count_not_one")
            if device_count:
                device_name = str(torch_module.cuda.get_device_name(0))
                if "P100" not in device_name.upper():
                    failures.append("gpu_is_not_p100")

    missing = [
        name for name in REQUIRED_INFERENCE_PACKAGES if versions.get(name) is None
    ]
    if missing:
        failures.append("required_inference_packages_missing")

    return {
        "stage": "b1_b2_kaggle_runtime_probe",
        "probe_complete": True,
        "ready": not failures,
        "failures": failures,
        "python_version": platform.python_version(),
        "cuda_available": cuda_available,
        "cuda_device_count": device_count,
        "device_name": device_name,
        "cuda_runtime": cuda_runtime,
        "packages": versions,
        "missing_required_packages": missing,
        "network_access_attempted": False,
        "private_input_accessed": False,
        "model_loaded": False,
    }


def main() -> None:
    report = runtime_report()
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
