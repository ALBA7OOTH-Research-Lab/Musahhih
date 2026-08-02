import json
import unittest

from scripts.summarize_training_token_budgets import (
    TokenBudgetError,
    percentile_nearest_rank,
    summarize_arm,
)


class FakeTokenizer:
    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False
        assert add_generation_prompt is False
        return "|".join(message["content"] for message in messages)

    def __call__(self, rendered, add_special_tokens, return_attention_mask):
        assert add_special_tokens is False
        assert return_attention_mask is False
        return {"input_ids": list(range(len(rendered.split("|")) + 1))}


def row(record_id, source="QALB-2014-L1"):
    return {
        "record_id": record_id,
        "prompt": [{"role": "user", "content": "private prompt"}],
        "completion": [{"role": "assistant", "content": "private completion"}],
        "source": source,
        "split": "train",
    }


class TrainingTokenBudgetTests(unittest.TestCase):
    def test_summarize_arm_is_corpus_text_free(self):
        summary = summarize_arm(
            [row("one"), row("two", source="Tibyan-corpus")], FakeTokenizer()
        )
        serialized = json.dumps(summary)
        self.assertEqual(summary["records"], 2)
        self.assertEqual(summary["formatted_tokens"], 6)
        self.assertNotIn("private prompt", serialized)
        self.assertNotIn("private completion", serialized)
        self.assertEqual(
            summary["source_totals"]["QALB-2014-L1"]["records"], 1
        )
        self.assertEqual(
            summary["source_totals"]["Tibyan-corpus"]["records"], 1
        )

    def test_percentile_nearest_rank_matches_frozen_convention(self):
        self.assertEqual(percentile_nearest_rank([1, 2, 3, 4], 0.95), 3)

    def test_percentile_rejects_empty_input(self):
        with self.assertRaises(TokenBudgetError):
            percentile_nearest_rank([], 0.95)


if __name__ == "__main__":
    unittest.main()
