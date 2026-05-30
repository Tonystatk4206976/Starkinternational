import pytest

from risk_tools import calculate_profit_taker_plan, format_profit_taker_summary


def test_profit_taker_plan_caps_sale_at_available_shares():
    plan = calculate_profit_taker_plan(
        current_price=10,
        current_shares=5,
        initial_principal=100,
    )

    assert plan.capital_to_recover == 50
    assert plan.shares_to_sell == 5
    assert plan.remaining_shares == 0


def test_profit_taker_summary_formats_compact_values():
    plan = calculate_profit_taker_plan(
        current_price=31.15,
        current_shares=420,
        initial_principal=10_000,
    )

    assert format_profit_taker_summary(plan, share_precision=2) == {
        "Shares to sell": "321.03",
        "Capital recovered": "$10,000.00",
        "Sale value": "$10,000.00",
        "Remaining shares": "98.97",
    }


def test_profit_taker_summary_rejects_negative_precision():
    plan = calculate_profit_taker_plan(10, 5, 25)

    with pytest.raises(ValueError, match="share_precision"):
        format_profit_taker_summary(plan, share_precision=-1)
