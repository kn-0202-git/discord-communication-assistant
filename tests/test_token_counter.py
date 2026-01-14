"""Token counter tests."""

from src.ai.token_counter import estimate_tokens, trim_context


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("a" * 4) == 1
    assert estimate_tokens("a" * 5) == 2


def test_trim_context_keeps_system_and_latest_message() -> None:
    context = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "aaaa"},
        {"role": "assistant", "content": "bbbb"},
        {"role": "user", "content": "cccc"},
    ]

    trimmed = trim_context(context, token_budget=3, prompt_text="pppp")

    assert trimmed == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "cccc"},
    ]
