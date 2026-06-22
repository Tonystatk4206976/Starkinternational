"""Risk-management helpers for sentiment-driven dashboards."""

from __future__ import annotations

import math
from dataclasses import dataclass


def _coerce_finite_float(value: float, field_name: str) -> float:
    """Return value as a finite float or raise a clear validation error."""
    if isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite")
    return number


@dataclass(frozen=True)
class ProfitTakerPlan:
    """Result of a principal de-risking calculation."""

    current_price: float
    current_shares: float
    initial_principal: float
    shares_to_sell: float
    capital_to_recover: float
    gross_sale_value: float
    remaining_shares: float


def calculate_profit_taker_plan(
    current_price: float,
    current_shares: float,
    initial_principal: float,
) -> ProfitTakerPlan:
    """Calculate how many shares to sell to recover initial principal.

    The logic assumes you want to de-risk by removing as much of your original
    principal as possible at the current market price.
    """
    current_price = _coerce_finite_float(current_price, "current_price")
    current_shares = _coerce_finite_float(current_shares, "current_shares")
    initial_principal = _coerce_finite_float(initial_principal, "initial_principal")

    if current_price <= 0:
        raise ValueError("current_price must be greater than 0")
    if current_shares < 0:
        raise ValueError("current_shares cannot be negative")
    if initial_principal < 0:
        raise ValueError("initial_principal cannot be negative")

    max_sale_value = current_price * current_shares
    capital_to_recover = min(initial_principal, max_sale_value)
    shares_to_sell = capital_to_recover / current_price
    remaining_shares = current_shares - shares_to_sell

    return ProfitTakerPlan(
        current_price=current_price,
        current_shares=current_shares,
        initial_principal=initial_principal,
        shares_to_sell=shares_to_sell,
        capital_to_recover=capital_to_recover,
        gross_sale_value=capital_to_recover,
        remaining_shares=remaining_shares,
    )


def format_reinvestment_playbook() -> list[str]:
    """Return concise reinvestment ideas for dashboard display text."""
    return [
        "Short-volatility (advanced/high-risk): trades that may benefit if volatility cools.",
        "Cash yield parking: hold realized gains in cash-equivalent funds while waiting.",
        "Contrarian index accumulation: scale into broad index exposure during fear spikes.",
    ]


def format_profit_taker_summary(
    plan: ProfitTakerPlan,
    *,
    currency_symbol: str = "$",
    share_decimals: int = 4,
) -> dict[str, str]:
    """Build compact key/value summary text for dashboard cards and tables.

    Args:
        plan: Profit-taker calculation result to summarize.
        currency_symbol: Prefix to use for money values.
        share_decimals: Number of decimal places to show for share quantities.

    Returns:
        Ordered metric labels and display values for compact dashboard cards.
    """
    if isinstance(share_decimals, bool) or not isinstance(share_decimals, int):
        raise TypeError("share_decimals must be an integer")
    if share_decimals < 0:
        raise ValueError("share_decimals cannot be negative")

    share_format = f",.{share_decimals}f"
    return {
        "Shares to sell": format(plan.shares_to_sell, share_format),
        "Capital recovered": f"{currency_symbol}{plan.capital_to_recover:,.2f}",
        "Sale value": f"{currency_symbol}{plan.gross_sale_value:,.2f}",
        "Remaining shares": format(plan.remaining_shares, share_format),
    }
