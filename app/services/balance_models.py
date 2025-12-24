from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TokenBalance(BaseModel):
    symbol: str = Field(description="Token symbol such as ETH or USDC.")
    amount: float = Field(description="Quantity of the token held.")
    usd_value: float = Field(description="USD valuation of the token at capture time.")
    contract_address: Optional[str] = Field(
        default=None, description="Contract address for the token when available."
    )


class BalanceReport(BaseModel):
    provider: str = Field(description="Provider or connector that produced the report.")
    address: str = Field(description="Wallet address for which the report was generated.")
    native_symbol: str = Field(description="Symbol of the native chain asset (ETH, SOL, etc.).")
    native_balance: float = Field(description="Amount of the native asset held by the wallet.")
    total_usd: float = Field(description="Total USD valuation across all assets.")
    tokens: List[TokenBalance] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    fiat_currency: str = Field(default="USD")
    raw: Dict[str, Any] = Field(default_factory=dict, description="Raw payload returned by the provider.")
    notes: Optional[str] = Field(default=None, description="Human-readable notes about the retrieval.")
