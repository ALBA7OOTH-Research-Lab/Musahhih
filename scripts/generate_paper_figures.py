"""Generate corpus-text-free figures for the MRL 2026 manuscript."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SYSTEM_ORDER = ("B1-P1", "B2-P1", "F1-P1", "F2-P1", "F3-P1")
SYSTEM_LABELS = {
    "B1-P1": "B1\nfive-shot",
    "B2-P1": "B2\nexpert-style",
    "F1-P1": "F1\nnatural",
    "F2-P1": "F2\nsynthetic",
    "F3-P1": "F3\nmixed",
}
CHECKPOINT_ARMS = ("F1-P1", "F2-P1", "F3-P1")
CHECKPOINT_LABELS = {"F1-P1": "F1 natural", "F2-P1": "F2 synthetic", "F3-P1": "F3 mixed"}


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


def load_checkpoint_losses(summary_path: Path) -> dict[str, tuple[list[float], int]]:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    selection = summary["primary_checkpoint_selection_development_loss"]
    if selection["records"] != 975 or not selection["lower_is_better"]:
        raise ValueError("Unexpected checkpoint-selection summary")

    values: dict[str, tuple[list[float], int]] = {}
    for arm_id in CHECKPOINT_ARMS:
        arm = selection["arms"][arm_id]
        losses = [float(arm["epoch_1"]), float(arm["epoch_2"])]
        selected_epoch = int(arm["selected_epoch"])
        if selected_epoch not in (1, 2):
            raise ValueError(f"Invalid selected epoch for {arm_id}")
        if losses[selected_epoch - 1] != min(losses):
            raise ValueError(f"Selected epoch is not the lower-loss epoch for {arm_id}")
        values[arm_id] = (losses, selected_epoch)
    return values


def generate_accuracy(summary_path: Path, output_path: Path) -> None:
    import matplotlib.pyplot as plt

    values = load_accuracies(summary_path)
    labels = [SYSTEM_LABELS[system_id] for system_id in SYSTEM_ORDER]
    fills = ["#d9d9d9"] * 2 + ["#737373"] * 3
    hatches = ["..", "xx", "", "..", "xx"]

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

    axis.axvline(1.5, color="#606060", linewidth=0.8, linestyle="--")
    axis.text(0.5, 37.0, "Prompt-only", ha="center", va="center", fontsize=8)
    axis.text(3.0, 37.0, "QLoRA fine-tuning", ha="center", va="center", fontsize=8)
    axis.set_xticks(range(len(labels)), labels)
    axis.set_ylabel("Exact-match accuracy (%)")
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


def generate_checkpoint_losses(summary_path: Path, output_path: Path) -> None:
    import matplotlib.pyplot as plt

    values = load_checkpoint_losses(summary_path)
    styles = {
        "F1-P1": ("#5f5f5f", "o", "-"),
        "F2-P1": ("#202020", "s", "--"),
        "F3-P1": ("#8a8a8a", "^", "-."),
    }
    fig, axis = plt.subplots(figsize=(3.25, 2.25))
    for arm_id in CHECKPOINT_ARMS:
        losses, selected_epoch = values[arm_id]
        color, marker, linestyle = styles[arm_id]
        axis.plot(
            (1, 2),
            losses,
            color=color,
            marker=marker,
            linestyle=linestyle,
            linewidth=1.2,
            markersize=4.5,
            label=CHECKPOINT_LABELS[arm_id],
        )
        axis.scatter(
            [selected_epoch],
            [losses[selected_epoch - 1]],
            s=58,
            facecolors="none",
            edgecolors=color,
            linewidths=1.0,
            zorder=4,
        )

    axis.set_xlabel("Training epoch")
    axis.set_ylabel("Development loss (lower is better)")
    axis.set_xticks((1, 2))
    axis.grid(axis="y", color="#d0d0d0", linewidth=0.5)
    axis.set_axisbelow(True)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(frameon=False, fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))
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
    parser.add_argument(
        "--checkpoint-output",
        type=Path,
        default=Path("paper/figures/checkpoint_dev_loss.pdf"),
    )
    args = parser.parse_args()
    generate_accuracy(args.summary, args.output)
    generate_checkpoint_losses(args.summary, args.checkpoint_output)


if __name__ == "__main__":
    main()
