"""
Cost estimation: the pricing table is in USD per 1,000,000 tokens.
"""
from app.config import compute_estimated_cost, settings


def test_table_prices_are_per_million_tokens():
    # 1,000,000 prompt tokens on gpt-4o-mini must cost exactly the listed $0.15.
    cost = compute_estimated_cost(
        served_model="gpt-4o-mini",
        prompt_tokens=1_000_000,
        completion_tokens=0,
        pricing_table=settings.PRICING_TABLE,
        global_prompt_price=0.0,
        global_completion_price=0.0,
    )
    assert cost == 0.15


def test_small_request_cost_is_fractions_of_a_cent():
    cost = compute_estimated_cost(
        served_model="gpt-4o",
        prompt_tokens=1_000,
        completion_tokens=500,
        pricing_table=settings.PRICING_TABLE,
        global_prompt_price=0.0,
        global_completion_price=0.0,
    )
    # 1000/1M * 2.50 + 500/1M * 10.00 = 0.0025 + 0.005
    assert round(cost, 6) == 0.0075


def test_unknown_model_uses_global_defaults():
    cost = compute_estimated_cost(
        served_model="some-local-model",
        prompt_tokens=2_000_000,
        completion_tokens=1_000_000,
        pricing_table=settings.PRICING_TABLE,
        global_prompt_price=0.10,
        global_completion_price=0.20,
    )
    assert round(cost, 6) == 0.40


def test_unknown_model_without_defaults_costs_zero():
    cost = compute_estimated_cost(
        served_model="some-local-model",
        prompt_tokens=10,
        completion_tokens=10,
        pricing_table=settings.PRICING_TABLE,
        global_prompt_price=0.0,
        global_completion_price=0.0,
    )
    assert cost == 0.0
