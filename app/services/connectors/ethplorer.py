from datetime import datetime
from typing import Any, Dict, List

import httpx

from ...core.config import settings
from ..balance_models import BalanceReport, TokenBalance
from ..errors import BalanceProviderError
from .base import BalanceConnector


class EthplorerConnector(BalanceConnector):
    name = "ethplorer"

    def __init__(self, provider: str, api_key: str | None = None) -> None:
        super().__init__(provider)
        self.api_key = api_key or settings.ethplorer_api_key
        self.base_url = "https://api.ethplorer.io"

    def fetch(self, address: str) -> BalanceReport:
        url = f"{self.base_url}/getAddressInfo/{address}"
        params = {"apiKey": self.api_key}
        try:
            response = httpx.get(url, params=params, timeout=20)
            response.raise_for_status()
        except httpx.HTTPError as exc:  # pragma: no cover - network failures are environment specific
            raise BalanceProviderError(
                provider=self.provider,
                message=f"Failed to fetch data from Ethplorer: {exc}",
                status_code=502,
            ) from exc

        payload: Dict[str, Any] = response.json()
        eth_balance = float(payload.get("ETH", {}).get("balance", 0.0))
        price_info = payload.get("ETH", {}).get("price", {})
        eth_price = float(price_info.get("rate", 0.0))
        tokens_data: List[Dict[str, Any]] = payload.get("tokens", [])

        tokens: List[TokenBalance] = []
        token_total_usd = 0.0
        for token in tokens_data:
            info = token.get("tokenInfo", {})
            decimals = int(info.get("decimals", 0) or 0)
            raw_balance = float(token.get("balance", 0.0))
            balance = raw_balance / (10 ** decimals) if decimals else raw_balance
            price = float(info.get("price", {}).get("rate", 0.0))
            usd_value = balance * price
            token_total_usd += usd_value
            tokens.append(
                TokenBalance(
                    symbol=info.get("symbol", "UNKNOWN"),
                    amount=balance,
                    usd_value=usd_value,
                    contract_address=info.get("address"),
                )
            )

        total_usd = eth_balance * eth_price + token_total_usd
        captured_at = datetime.utcnow()

        return BalanceReport(
            provider=self.provider,
            address=address,
            native_symbol="ETH",
            native_balance=eth_balance,
            total_usd=total_usd,
            tokens=tokens,
            retrieved_at=captured_at,
            raw=payload,
            notes="Data retrieved from Ethplorer",
        )
