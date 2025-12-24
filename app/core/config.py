from pathlib import Path
from typing import Dict

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str = Field(
        default="sqlite:///./wallet_tracker.db",
        description="SQL database URL for persisting wallet data.",
    )
    static_balance_file: Path = Field(
        default=Path("data/static_balances.json"),
        description="Path to the JSON file that stores static balance snapshots used for offline providers.",
    )
    ethplorer_api_key: str = Field(
        default="freekey",
        description="API key used when calling the Ethplorer API for Ethereum balances.",
    )
    provider_connector_map: Dict[str, str] = Field(
        default_factory=lambda: {
            "WalaWallet": "static",
            "Dormit": "static",
            "Wicket": "static",
            "Exchange": "static",
        },
        description="Mapping of provider names to balance connector identifiers.",
    )

    class Config:
        env_prefix = "WALLET_TRACKER_"
        case_sensitive = False


settings = Settings()
