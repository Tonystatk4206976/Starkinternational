from abc import ABC, abstractmethod
from typing import Optional

from ..balance_models import BalanceReport
from ..errors import BalanceProviderError


class BalanceConnector(ABC):
    """Abstract connector used to fetch wallet balance information."""

    name: str

    def __init__(self, provider: str) -> None:
        self.provider = provider

    @abstractmethod
    def fetch(self, address: str) -> BalanceReport:
        """Retrieve the balances for the provided address."""

    def handle_not_found(self, address: str) -> BalanceReport:
        raise BalanceProviderError(
            provider=self.provider,
            message=f"No static balance data found for {address}",
        )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.__class__.__name__}(provider={self.provider!r})"
