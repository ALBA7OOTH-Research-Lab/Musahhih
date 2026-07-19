import unittest

from scripts.validate_tibyan_token_lengths import measure_lengths


class FakeTokenizer:
    def __len__(self):
        return 42

    def apply_chat_template(self, messages, tokenize, add_generation_prompt):
        assert tokenize is False
        assert add_generation_prompt is False
        return "rendered " + messages[-1]["content"]

    def __call__(self, rendered, add_special_tokens, return_attention_mask):
        assert add_special_tokens is False
        assert return_attention_mask is False
        return {"input_ids": list(range(len(rendered.split()) + 1))}


class TibyanTokenLengthTests(unittest.TestCase):
    def test_measure_lengths_returns_only_text_free_aggregates(self):
        rows = [
            {
                "record_id": "record-hash",
                "passage": "private passage",
                "erroneous_word": "private",
                "gold_correction": "correct",
            }
        ]
        summary = measure_lengths(rows, FakeTokenizer(), "4.56.2")
        self.assertEqual(summary["records"], 1)
        self.assertIs(summary["contains_corpus_text"], False)
        self.assertNotIn("private", str(summary))
        self.assertIs(summary["model_weights_loaded"], False)
        self.assertIs(summary["training_or_inference_executed"], False)


if __name__ == "__main__":
    unittest.main()
