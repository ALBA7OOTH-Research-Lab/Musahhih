import hashlib
import json
import unittest

from scripts.prepare_tibyan_f2_f3 import (
    TibyanManifestError,
    assign_source_groups,
    derive_candidates,
    forced_substitutions,
    prepare_manifest,
    sha256_text,
)


class TibyanManifestTests(unittest.TestCase):
    def test_forced_substitution_is_found_without_a_backtrace_tiebreak(self):
        distance, substitutions = forced_substitutions(
            ["alpha", "wrong", "omega"], ["alpha", "right", "omega"]
        )
        self.assertEqual(distance, 1)
        self.assertEqual(substitutions, [(1, 1, "wrong", "right")])

    def test_insertions_and_deletions_are_not_invented_as_substitutions(self):
        distance, substitutions = forced_substitutions(
            ["alpha", "omega"], ["alpha", "added", "omega"]
        )
        self.assertEqual(distance, 1)
        self.assertEqual(substitutions, [])

    def test_repeated_erroneous_token_is_ineligible_for_positionless_prompt(self):
        rows, summary = derive_candidates(
            ["same wrong same wrong"], ["same right same wrong"]
        )
        self.assertEqual(rows, [])
        self.assertEqual(summary["pairs_with_forced_substitution"], 1)
        self.assertEqual(
            summary["pairs_with_unique_error_forced_substitution"], 0
        )

    def test_whole_pair_classification_is_emitted_by_canonical_builder(self):
        _, summary = derive_candidates(
            ["same", "alpha wrong", "one two", "short"],
            ["same", "alpha right", "three four", "short added"],
        )
        self.assertEqual(
            summary["whole_pair_classification"],
            {
                "eligible_single_substitution": 1,
                "identical": 1,
                "multiple_token_differences": 1,
                "token_count_mismatch": 1,
            },
        )

    def test_exact_shared_side_forms_one_connected_group(self):
        rows, _ = derive_candidates(
            ["alpha wrong", "alpha wrong"], ["alpha right", "alpha other"]
        )
        groups = assign_source_groups(rows)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(groups), 1)
        self.assertEqual(
            rows[0]["source_group_id"], rows[1]["source_group_id"]
        )

    def test_prepare_manifest_excludes_a_whole_group_on_test_overlap(self):
        erroneous = ["alpha wrong", "beta bad", "gamma false"]
        corrected = ["alpha right", "beta good", "gamma true"]
        test_hash = sha256_text(erroneous[0])
        with self.assertRaisesRegex(
            TibyanManifestError, r"Only \d+ Tibyan training groups"
        ):
            prepare_manifest(
                erroneous,
                corrected,
                {"test": {test_hash}, "train_development": set()},
                set(),
                train_limit=3,
            )

    def test_public_summary_has_no_corpus_text_and_f3_is_nested(self):
        erroneous = [f"record{i} wrong" for i in range(20)]
        corrected = [f"record{i} right" for i in range(20)]
        payloads, summary = prepare_manifest(
            erroneous,
            corrected,
            {"test": set(), "train_development": set()},
            set(),
            train_limit=2,
        )
        public = payloads["tibyan_manifest_summary.json"].decode("utf-8")
        self.assertNotIn(" wrong", public)
        self.assertNotIn(" right", public)
        self.assertIs(summary["contains_corpus_text"], False)
        self.assertEqual(summary["f3_synthetic_nested_records"], 1)
        train_rows = [
            json.loads(line)
            for line in payloads["tibyan_train_selection.jsonl"]
            .decode()
            .splitlines()
        ]
        expected = hashlib.sha256(
            (train_rows[0]["record_id"] + "\n").encode()
        ).hexdigest()
        self.assertEqual(
            summary["f3_synthetic_selection_record_id_sha256"], expected
        )


if __name__ == "__main__":
    unittest.main()
