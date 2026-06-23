import unittest

from scripts.nahw_baseline_utils import parse_model_response, summarize_predictions


class ParseModelResponseTests(unittest.TestCase):
    def test_removes_only_outer_formatting(self):
        parsed, warnings = parse_model_response("  **«مُصَحَّحة»**  ")
        self.assertEqual(parsed, "مُصَحَّحة")
        self.assertIn("outer_formatting_removed", warnings)

    def test_preserves_internal_arabic_punctuation_and_letters(self):
        parsed, warnings = parse_model_response("إجابة،أخرى")
        self.assertEqual(parsed, "إجابة،أخرى")
        self.assertEqual(warnings, [])

    def test_does_not_discard_extra_lines(self):
        parsed, warnings = parse_model_response("الإجابة\nشرح")
        self.assertEqual(parsed, "الإجابة\nشرح")
        self.assertIn("multiple_lines", warnings)

    def test_flags_empty_multitoken_and_explanation_like_outputs(self):
        self.assertIn("empty_output", parse_model_response(" \n ")[1])
        self.assertIn("multiple_words", parse_model_response("كلمتان هنا")[1])
        self.assertIn(
            "explanation_like",
            parse_model_response("الكلمة المصححة: مثال")[1],
        )


class SummaryTests(unittest.TestCase):
    def test_outer_formatting_cleanup_is_not_counted_as_suspicious(self):
        rows = [{
            "exact_match": True,
            "parsed_correction": "مثال",
            "parsing_warnings": ["outer_formatting_removed"],
        }]
        self.assertEqual(summarize_predictions(rows)["suspicious_output_count"], 0)

    def test_counts_exact_empty_and_suspicious_outputs(self):
        rows = [
            {"exact_match": True, "parsed_correction": "أ", "parsing_warnings": []},
            {
                "exact_match": False,
                "parsed_correction": "",
                "parsing_warnings": ["empty_output"],
            },
            {
                "exact_match": False,
                "parsed_correction": "كلمتان هنا",
                "parsing_warnings": ["multiple_words"],
            },
        ]
        summary = summarize_predictions(rows)
        self.assertEqual(summary["number_of_records"], 3)
        self.assertEqual(summary["number_correct"], 1)
        self.assertEqual(summary["exact_match_accuracy"], 1 / 3)
        self.assertEqual(summary["invalid_or_empty_count"], 1)
        self.assertEqual(summary["parsing_failure_count"], 1)
        self.assertEqual(summary["suspicious_output_count"], 2)
        self.assertEqual(summary["multi_token_count"], 1)


if __name__ == "__main__":
    unittest.main()
