"""Generate corpus-text-free figures for the MRL 2026 manuscript."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SYSTEM_ORDER = ("B0-P1", "B1-P1", "B2-P1", "F1-P1", "F2-P1", "F3-P1")
SYSTEM_LABELS = {
    "B0-P1": "B0\nzero-shot",
    "B1-P1": "B1\nfive-shot",
    "B2-P1": "B2\nexpert-style",
    "F1-P1": "F1\nnatural",
    "F2-P1": "F2\nsynthetic",
    "F3-P1": "F3\nmixed",
}


def load_accuracies(summary_path: Path) -> list[float]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    evaluation = summary["primary_evaluation"]
    if evaluation["records"] != 511:
        raise ValueError("Expected the frozen 511-record Nahw-Passage evaluation")

    systems = evaluation["systems"]
    values: list[float] = []
    for system_id in SYSTEM_ORDER:
        system = systems[system_id]
        if system["result_status"] != "accepted":
            raise ValueError(f"{system_id} is not an accepted final result")
        correct = int(system["correct"])
        accuracy = float(system["accuracy"])
        if abs(accuracy - correct / evaluation["records"]) > 1e-12:
            raise ValueError(f"{system_id} count and accuracy disagree")
        values.append(accuracy * 100)
    return values


def generate(summary_path: Path, output_path: Path) -> None:
    import matplotlib.pyplot as plt

    values = load_accuracies(summary_path)
    labels = [SYSTEM_LABELS[system_id] for system_id in SYSTEM_ORDER]
    fills = ["#d9d9d9"] * 3 + ["#737373"] * 3
    hatches = ["", "..", "xx", "", "..", "xx"]

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
        }
    )
    fig, axis = plt.subplots(figsize=(6.8, 2.55))
    bars = axis.bar(
        range(len(values)),
        values,
        color=fills,
        edgecolor="#202020",
        linewidth=0.8,
    )
    for bar, hatch in zip(bars, hatches, strict=True):
        bar.set_hatch(hatch)

    for bar, value in zip(bars, values, strict=True):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.8,
            f"{value:.2f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    axis.axvline(2.5, color="#606060", linewidth=0.8, linestyle="--")
    axis.text(1.0, 37.0, "Prompt-only", ha="center", va="center", fontsize=8)
    axis.text(4.0, 37.0, "QLoRA fine-tuning", ha="center", va="center", fontsize=8)
    axis.set_xticks(range(len(labels)), labels)
    axis.set_ylabel("Exact correction accuracy (%)")
    axis.set_ylim(0, 40)
    axis.set_yticks((0, 10, 20, 30, 40))
    axis.grid(axis="y", color="#d0d0d0", linewidth=0.5)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.5)
    fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--summary",
        type=Path,
        default=Path("results/research_results_consolidated.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("paper/figures/system_accuracy.pdf"),
    )
    args = parser.parse_args()
    generate(args.summary, args.output)


if __name__ == "__main__":
    main()
