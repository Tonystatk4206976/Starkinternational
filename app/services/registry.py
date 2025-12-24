from functools import lru_cache
from typing import Dict

from ..core.config import settings
from .connectors.base import BalanceConnector
from .connectors.ethplorer import EthplorerConnector
from .connectors.static import StaticConnector


@lru_cache(maxsize=32)
def _build_connector(provider: str, spec: str) -> BalanceConnector:
    if spec.startswith("static"):
        return StaticConnector(provider=provider)
    if spec == "ethplorer":
        return EthplorerConnector(provider=provider)
    raise ValueError(f"Unknown connector specification: {spec}")


def get_connector(provider: str) -> BalanceConnector:
    spec = settings.provider_connector_map.get(provider)
    if not spec:
        spec = "static"
    return _build_connector(provider, spec)
