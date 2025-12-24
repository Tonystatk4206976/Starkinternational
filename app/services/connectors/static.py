import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ...core.config import settings
from ..balance_models import BalanceReport, TokenBalance
from ..errors import BalanceProviderError
from .base import BalanceConnector


class StaticConnector(BalanceConnector):
    """Connector that reads balance snapshots from a local JSON file.

    The JSON file must follow the structure:

    ```json
    {
        "ProviderName": {
            "wallet_address": {
                "captured_at": "2023-10-01T00:00:00Z",
                "native_symbol": "ETH",
                "native_balance": 1.234,
                "total_usd": 3500.12,
                "tokens": [
                    {"symbol": "ETH", "amount": 1.234, "usd_value": 3500.12}
                ]
            }
        }
    }
    ```
    """

    name = "static"

    def __init__(self, provider: str, data_path: Path | None = None) -> None:
        super().__init__(provider)
        self.data_path = data_path or settings.static_balance_file
        self._data: Dict[str, Dict[str, Dict[str, Any]]] | None = None

    @property
    def data(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        if self._data is None:
            path = Path(self.data_path)
            if not path.exists():
                raise BalanceProviderError(
                    provider=self.provider,
                    message=f"Static balance file not found at {path}",
                    status_code=500,
                )
            with path.open("r", encoding="utf-8") as fp:
                self._data = json.load(fp)
        return self._data

    def fetch(self, address: str) -> BalanceReport:
        provider_data = self.data.get(self.provider)
        if not provider_data:
            raise BalanceProviderError(
                provider=self.provider,
                message=f"No static balance data configured for provider {self.provider}",
            )

        wallet_data = provider_data.get(address)
        if not wallet_data:
            raise BalanceProviderError(
                provider=self.provider,
                message=f"Static data for address {address} not found under provider {self.provider}",
                status_code=404,
            )

        captured_at = datetime.fromisoformat(wallet_data.get("captured_at"))
        tokens = [
            TokenBalance(
                symbol=token.get("symbol"),
                amount=float(token.get("amount", 0.0)),
                usd_value=float(token.get("usd_value", 0.0)),
                contract_address=token.get("contract_address"),
            )
            for token in wallet_data.get("tokens", [])
        ]

        return BalanceReport(
            provider=self.provider,
            address=address,
            native_symbol=wallet_data.get("native_symbol", "N/A"),
            native_balance=float(wallet_data.get("native_balance", 0.0)),
            total_usd=float(wallet_data.get("total_usd", 0.0)),
            tokens=tokens,
            retrieved_at=captured_at,
            raw=wallet_data,
            notes=wallet_data.get("notes"),
        )
