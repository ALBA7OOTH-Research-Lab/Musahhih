import json

import pytest

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


def test_summarize_arm_is_corpus_text_free():
    summary = summarize_arm(
        [row("one"), row("two", source="Tibyan-corpus")], FakeTokenizer()
    )
    serialized = json.dumps(summary)
    assert summary["records"] == 2
    assert summary["formatted_tokens"] == 6
    assert "private prompt" not in serialized
    assert "private completion" not in serialized
    assert summary["source_totals"]["QALB-2014-L1"]["records"] == 1
    assert summary["source_totals"]["Tibyan-corpus"]["records"] == 1


def test_percentile_nearest_rank_matches_frozen_convention():
    assert percentile_nearest_rank([1, 2, 3, 4], 0.95) == 3


def test_percentile_rejects_empty_input():
    with pytest.raises(TokenBudgetError):
        percentile_nearest_rank([], 0.95)
