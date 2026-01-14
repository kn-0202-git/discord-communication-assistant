"""Token counter utilities.

簡易なトークン数の概算と、コンテキストのトリムを行う。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import yaml

DEFAULT_TOKEN_BUDGET = 6000
DEFAULT_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """文字数からトークン数を概算する."""
    if not text:
        return 0
    return math.ceil(len(text) / DEFAULT_CHARS_PER_TOKEN)


def estimate_message_tokens(message: dict[str, Any]) -> int:
    """メッセージのトークン数を概算する."""
    return estimate_tokens(str(message.get("content", "")))


def get_token_budget(config_path: Path | None = None) -> int:
    """config.yamlからトークン上限を取得する."""
    path = config_path or Path("config.yaml")
    if not path.exists():
        return DEFAULT_TOKEN_BUDGET

    try:
        with open(path, encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
    except Exception:
        return DEFAULT_TOKEN_BUDGET

    ai_config = config.get("ai") or {}
    value = ai_config.get("token_budget")
    if isinstance(value, int) and value > 0:
        return value

    return DEFAULT_TOKEN_BUDGET


def trim_context(
    context: list[dict[str, str]],
    token_budget: int,
    prompt_text: str = "",
    system_prompt: str = "",
) -> list[dict[str, str]]:
    """コンテキストをトークン上限に収まるようにトリムする."""
    if token_budget <= 0:
        return []

    prompt_tokens = estimate_tokens(prompt_text) + estimate_tokens(system_prompt)
    message_tokens = [estimate_message_tokens(msg) for msg in context]
    total_tokens = prompt_tokens + sum(message_tokens)

    if total_tokens <= token_budget:
        return list(context)

    non_system_indices = [i for i, msg in enumerate(context) if msg.get("role") != "system"]

    while total_tokens > token_budget and len(non_system_indices) > 1:
        remove_index = non_system_indices.pop(0)
        total_tokens -= message_tokens[remove_index]

    keep_indices = {i for i, msg in enumerate(context) if msg.get("role") == "system"} | set(
        non_system_indices
    )

    return [msg for i, msg in enumerate(context) if i in keep_indices]
