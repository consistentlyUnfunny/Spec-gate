from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UsageReport:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0


def extract_token_usage(response: Any) -> dict[str, int]:
    """
    Extracts token usage from common LangChain provider response shapes.
    """
    metadata = getattr(response, "response_metadata", {}) or {}
    usage_metadata = getattr(response, "usage_metadata", {}) or {}

    raw_usage = (
        usage_metadata
        or metadata.get("token_usage")
        or metadata.get("usage")
        or {}
    )

    input_tokens = _first_int(
        raw_usage,
        "input_tokens",
        "prompt_tokens",
        "prompt_token_count",
    )
    output_tokens = _first_int(
        raw_usage,
        "output_tokens",
        "completion_tokens",
        "completion_token_count",
    )
    total_tokens = _first_int(raw_usage, "total_tokens", "total_token_count")

    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def calculate_usage_report(
    response: Any,
    input_cost_per_million_tokens: float,
    output_cost_per_million_tokens: float,
) -> UsageReport:
    usage = extract_token_usage(response)
    cost = (
        usage["input_tokens"] * input_cost_per_million_tokens
        + usage["output_tokens"] * output_cost_per_million_tokens
    ) / 1_000_000

    return UsageReport(
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        total_tokens=usage["total_tokens"],
        cost_usd=cost,
    )


def _first_int(data: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = data.get(key)
        if isinstance(value, int):
            return value
    return 0
