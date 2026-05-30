"""Risk-management helpers for sentiment-driven dashboards."""

from __future__ import annotations

from dataclasses import dataclass


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
        current_price=float(current_price),
        current_shares=float(current_shares),
        initial_principal=float(initial_principal),
        shares_to_sell=float(shares_to_sell),
        capital_to_recover=float(capital_to_recover),
        gross_sale_value=float(capital_to_recover),
        remaining_shares=float(remaining_shares),
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
    share_precision: int = 4,
) -> dict[str, str]:
    """Build compact key/value summary text for dashboard cards and tables."""
    if share_precision < 0:
        raise ValueError("share_precision cannot be negative")

    return {
        "Shares to sell": f"{plan.shares_to_sell:,.{share_precision}f}",
        "Capital recovered": f"{currency_symbol}{plan.capital_to_recover:,.2f}",
        "Sale value": f"{currency_symbol}{plan.gross_sale_value:,.2f}",
        "Remaining shares": f"{plan.remaining_shares:,.{share_precision}f}",
    }
