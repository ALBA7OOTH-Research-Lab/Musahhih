import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts.prepare_f1_natural_records import (
    AdapterError, build_split, eligible_actions, safe_output_dir,
)


def row(**changes):
    base = {
        "record_key": "synthetic:1", "year": 2014, "track": "L1", "split": "train",
        "line_number": 1,
        "sent_member": "ROOT/data/2014/train/QALB-2014-L1-Train.sent",
        "m2_member": "ROOT/data/2014/train/QALB-2014-L1-Train.m2",
        "source_sha256": hashlib.sha256(b"BAD TOKEN HERE").hexdigest(),
        "correction_sha256": hashlib.sha256(b"FIXED TOKEN HERE").hexdigest(),
        "duplicate_source_within_split": False,
        "exact_source_overlap_with_qalb_test": False,
        "exact_source_overlap_with_nahw": False,
        "eligible_for_training": True,
    }
    base.update(changes)
    return base


def synthetic_zip(path: Path, action="A 1 2|||TYPE_IGNORED|||FIXED|||REQUIRED|||-NONE-|||0"):
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ROOT/data/2014/train/QALB-2014-L1-Train.sent", "doc1 BAD TOKEN HERE\n")
        archive.writestr("ROOT/data/2014/train/QALB-2014-L1-Train.m2", f"S BAD TOKEN HERE\n{action}\n")


def test_single_token_annotator_zero_action_is_eligible():
    actions = ["A 1 2|||ANY_LABEL|||FIXED|||REQUIRED|||-NONE-|||0"]
    result = eligible_actions("BAD TOKEN HERE", actions, "synthetic:1")
    assert len(result) == 1
    assert result[0]["error"] == "TOKEN"
    assert result[0]["correction"] == "FIXED"


@pytest.mark.parametrize("action", [
    "A 1 2|||TYPE|||FIXED|||REQUIRED|||-NONE-|||1",
    "A 1 3|||TYPE|||FIXED|||REQUIRED|||-NONE-|||0",
    "A 1 2|||TYPE|||TWO WORDS|||REQUIRED|||-NONE-|||0",
    "A 1 2|||TYPE|||-NONE-|||REQUIRED|||-NONE-|||0",
])
def test_ineligible_m2_actions_are_rejected(action):
    assert eligible_actions("BAD TOKEN HERE", [action], "synthetic:1") == []


def test_build_split_uses_source_hash_and_never_returns_labels(tmp_path):
    archive_path = tmp_path / "fixture.zip"
    synthetic_zip(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        edits, exclusions = build_split(archive, [row()], "train")
    assert len(edits) == 1
    assert "TYPE_IGNORED" not in json.dumps(edits)
    assert exclusions == {"document_filter": 0, "no_eligible_action": 0}


def test_build_split_fails_on_source_hash_mismatch(tmp_path):
    archive_path = tmp_path / "fixture.zip"
    synthetic_zip(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(AdapterError, match="Source integrity mismatch"):
            build_split(archive, [row(source_sha256="0" * 64)], "train")


def test_test_split_cannot_enter_training(tmp_path):
    archive_path = tmp_path / "fixture.zip"
    synthetic_zip(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        edits, exclusions = build_split(
            archive,
            [row(split="test", eligible_for_training=False)],
            "train",
        )
    assert edits == []
    assert exclusions["document_filter"] == 1


def test_manifest_cannot_redirect_training_to_test_member(tmp_path):
    archive_path = tmp_path / "fixture.zip"
    synthetic_zip(archive_path)
    with zipfile.ZipFile(archive_path) as archive:
        with pytest.raises(AdapterError, match="frozen split"):
            build_split(
                archive,
                [row(sent_member="ROOT/data/2014/test/QALB-2014-L1-Test.sent")],
                "train",
            )


def test_private_output_must_stay_under_processed(tmp_path, monkeypatch):
    import scripts.prepare_f1_natural_records as module
    monkeypatch.setattr(module, "ROOT", tmp_path)
    allowed = tmp_path / "data" / "processed" / "f1"
    assert safe_output_dir(allowed) == allowed.resolve()
    with pytest.raises(AdapterError, match="must stay"):
        safe_output_dir(tmp_path / "outputs")
