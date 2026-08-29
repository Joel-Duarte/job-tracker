from app.services.pricing_service import (
    calculate_cost_and_savings,
    extract_usage_from_payload,
    get_all_pricing_rates,
    reset_pricing_rates,
    update_pricing_rate_override,
)


def test_pricing_rates_crud():
    # Test getting default rates
    rates = get_all_pricing_rates()
    assert len(rates) > 5
    baseline = next(r for r in rates if r["key"] == "local_baseline")
    assert baseline["input_cost_per_million"] == 0.15
    assert baseline["output_cost_per_million"] == 0.60

    # Test updating a rate override
    updated = update_pricing_rate_override("gpt-4o", 2.00, 8.00)
    assert updated["input_cost_per_million"] == 2.00
    assert updated["output_cost_per_million"] == 8.00

    cost, savings = calculate_cost_and_savings(
        "gpt-4o", 1_000_000, 1_000_000, is_local=False
    )
    assert cost == 10.00
    assert savings == 0.0

    # Test reset
    reset_pricing_rates()
    rates_after = get_all_pricing_rates()
    gpt4o_reset = next(r for r in rates_after if r["key"] == "gpt-4o")
    assert gpt4o_reset["input_cost_per_million"] == 2.50


def test_calculate_cost_and_savings_local():
    # Local execution should have 0 actual cost and positive cloud savings
    cost, savings = calculate_cost_and_savings(
        model_name="qwen/qwen3.5-9b",
        input_tokens=100_000,
        output_tokens=50_000,
        is_local=True,
    )
    assert cost == 0.0
    # Baseline: 100k * (0.15 / 1M) + 50k * (0.60 / 1M) = 0.015 + 0.030 = 0.045
    assert savings == 0.045


def test_calculate_cost_and_savings_cloud():
    # Paid cloud model (Claude 3.5 Sonnet: $3.00/1M in, $15.00/1M out)
    cost, savings = calculate_cost_and_savings(
        model_name="claude-3-5-sonnet-20241022",
        input_tokens=100_000,
        output_tokens=20_000,
        is_local=False,
    )
    assert savings == 0.0
    # 100k * 3/1M + 20k * 15/1M = 0.30 + 0.30 = 0.60
    assert cost == 0.60


def test_extract_usage_from_payload_direct():
    payload = {
        "prompt_tokens": 500,
        "completion_tokens": 200,
        "total_tokens": 700,
        "model_name": "gpt-4o-mini",
        "is_local": False,
        "duration_ms": 1200,
    }
    extracted = extract_usage_from_payload(payload)
    assert extracted["total_tokens"] == 700
    assert extracted["prompt_tokens"] == 500
    assert extracted["completion_tokens"] == 200
    assert extracted["estimated_cost"] > 0
    assert extracted["duration_seconds"] == 1.2


def test_extract_usage_from_payload_langchain():
    payload = {
        "outputs": {
            "generations": [
                [
                    {
                        "message": {
                            "usage_metadata": {
                                "input_tokens": 300,
                                "output_tokens": 150,
                                "total_tokens": 450,
                            },
                            "response_metadata": {
                                "model_name": "gemini-2.0-flash",
                            },
                        }
                    }
                ]
            ]
        },
        "duration_ms": 850,
    }
    extracted = extract_usage_from_payload(payload)
    assert extracted["total_tokens"] == 450
    assert extracted["prompt_tokens"] == 300
    assert extracted["completion_tokens"] == 150
    assert extracted["model_name"] == "gemini-2.0-flash"
    assert extracted["duration_seconds"] == 0.85


def test_calculate_comparative_provider_costs():
    from app.services.pricing_service import calculate_comparative_provider_costs

    comparative = calculate_comparative_provider_costs(
        monthly_input_tokens=100_000,
        monthly_output_tokens=50_000,
        current_spend_usd=0.0,
        is_current_local=True,
    )
    assert len(comparative) >= 5
    local_entry = next(c for c in comparative if c["is_local"])
    assert local_entry["simulated_cost_usd"] == 0.0
    assert local_entry["status"] == "identical"

    gpt4o_entry = next(
        c
        for c in comparative
        if "GPT-4o" in c["model_name"] and "Mini" not in c["model_name"]
    )
    # 100k * 2.50/1M + 50k * 10.00/1M = 0.25 + 0.50 = 0.75
    assert gpt4o_entry["simulated_cost_usd"] == 0.75
    assert gpt4o_entry["status"] == "more_expensive"
    assert gpt4o_entry["diff_usd"] == 0.75


def test_calculate_cost_custom_provider_rates():
    # Custom endpoint with custom rates: $1.00/1M in, $2.00/1M out
    cost, savings = calculate_cost_and_savings(
        model_name="my-custom-model",
        input_tokens=200_000,
        output_tokens=100_000,
        is_local=False,
        custom_input_cost_per_million=1.00,
        custom_output_cost_per_million=2.00,
    )
    # 200k * 1.00/1M + 100k * 2.00/1M = 0.20 + 0.20 = 0.40
    assert cost == 0.40
    assert savings == 0.0
