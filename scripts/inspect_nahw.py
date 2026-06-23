#!/usr/bin/env python3
"""Inspect the schemas and basic counts of the official Nahw data files."""

from pathlib import Path
import csv
import json
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "nahw"


def inspect_json() -> None:
    path = RAW / "Nahw-Passage.json"
    with path.open("r", encoding="utf-8") as f:
        rows = json.load(f)

    print("\nNahw-Passage")
    print("records:", len(rows))
    print("unique passages:", len({r["passage_id"] for r in rows}))
    print("fields:", sorted(rows[0].keys()))
    print("empty corrections:", sum(not r.get("correction", "").strip() for r in rows))
    print("empty explanations:", sum(not r.get("explanation", "").strip() for r in rows))
    print("most repeated error strings:", Counter(r["error"] for r in rows).most_common(10))


def inspect_csv(filename: str) -> None:
    path = RAW / filename
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"\n{filename}")
    print("records:", len(rows))
    print("fields:", reader.fieldnames)
    if rows:
        empties = {
            field: sum(not (row.get(field) or "").strip() for row in rows)
            for field in reader.fieldnames or []
        }
        print("empty values:", empties)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    missing = [
        p
        for p in [
            RAW / "Nahw-Passage.json",
            RAW / "Nahw-MCQ.csv",
            RAW / "Synthetic_10K_Grammar_Questions.csv",
        ]
        if not p.exists()
    ]
    if missing:
        raise SystemExit("Missing data. Run scripts/download_nahw.py first.")

    inspect_json()
    inspect_csv("Nahw-MCQ.csv")
    inspect_csv("Synthetic_10K_Grammar_Questions.csv")


if __name__ == "__main__":
    main()
