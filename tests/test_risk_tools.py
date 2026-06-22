import math

import pytest

from risk_tools import calculate_profit_taker_plan, format_profit_taker_summary


def test_calculate_profit_taker_plan_caps_recovery_to_current_value():
    plan = calculate_profit_taker_plan(
        current_price=10,
        current_shares=5,
        initial_principal=100,
    )

    assert plan.capital_to_recover == 50
    assert plan.shares_to_sell == 5
    assert plan.remaining_shares == 0


def test_calculate_profit_taker_plan_recovers_partial_position():
    plan = calculate_profit_taker_plan(
        current_price=25,
        current_shares=20,
        initial_principal=100,
    )

    assert plan.capital_to_recover == 100
    assert plan.shares_to_sell == 4
    assert plan.remaining_shares == 16


def test_calculate_profit_taker_plan_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="current_price"):
        calculate_profit_taker_plan(0, 10, 100)

    with pytest.raises(ValueError, match="current_shares"):
        calculate_profit_taker_plan(10, -1, 100)

    with pytest.raises(ValueError, match="initial_principal"):
        calculate_profit_taker_plan(10, 10, -1)


def test_calculate_profit_taker_plan_rejects_invalid_numeric_inputs():
    with pytest.raises(TypeError, match="current_price must be numeric"):
        calculate_profit_taker_plan(True, 10, 100)

    with pytest.raises(TypeError, match="current_shares must be numeric"):
        calculate_profit_taker_plan(10, "shares", 100)

    with pytest.raises(ValueError, match="current_price must be finite"):
        calculate_profit_taker_plan(math.nan, 10, 100)

    with pytest.raises(ValueError, match="current_shares must be finite"):
        calculate_profit_taker_plan(10, math.inf, 100)

    with pytest.raises(ValueError, match="initial_principal must be finite"):
        calculate_profit_taker_plan(10, 10, -math.inf)


def test_format_profit_taker_summary_supports_compact_metric_cards():
    plan = calculate_profit_taker_plan(31.15, 420, 10_000)

    assert format_profit_taker_summary(plan, share_decimals=2) == {
        "Shares to sell": "321.03",
        "Capital recovered": "$10,000.00",
        "Sale value": "$10,000.00",
        "Remaining shares": "98.97",
    }


def test_format_profit_taker_summary_rejects_negative_share_decimals():
    plan = calculate_profit_taker_plan(10, 5, 50)

    with pytest.raises(ValueError, match="share_decimals"):
        format_profit_taker_summary(plan, share_decimals=-1)


def test_format_profit_taker_summary_rejects_non_integer_share_decimals():
    plan = calculate_profit_taker_plan(10, 5, 50)

    with pytest.raises(TypeError, match="share_decimals"):
        format_profit_taker_summary(plan, share_decimals=1.5)

    with pytest.raises(TypeError, match="share_decimals"):
        format_profit_taker_summary(plan, share_decimals=True)
