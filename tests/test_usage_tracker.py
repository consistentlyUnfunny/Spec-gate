from types import SimpleNamespace

from specgate.utils.usage_tracker import calculate_usage_report, extract_token_usage


def test_extract_token_usage_reads_usage_metadata():
    response = SimpleNamespace(
        usage_metadata={
            "input_tokens": 100,
            "output_tokens": 25,
            "total_tokens": 125,
        }
    )

    assert extract_token_usage(response) == {
        "input_tokens": 100,
        "output_tokens": 25,
        "total_tokens": 125,
    }


def test_extract_token_usage_reads_openai_token_usage_metadata():
    response = SimpleNamespace(
        response_metadata={
            "token_usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
            }
        }
    )

    assert extract_token_usage(response) == {
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
    }


def test_calculate_usage_report_estimates_cost():
    response = SimpleNamespace(
        usage_metadata={
            "input_tokens": 1_000_000,
            "output_tokens": 500_000,
        }
    )

    report = calculate_usage_report(
        response,
        input_cost_per_million_tokens=1.0,
        output_cost_per_million_tokens=2.0,
    )

    assert report.input_tokens == 1_000_000
    assert report.output_tokens == 500_000
    assert report.total_tokens == 1_500_000
    assert report.cost_usd == 2.0
