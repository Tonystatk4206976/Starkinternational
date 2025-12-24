"""Utility script to seed the database with sample wallets and snapshots."""

from datetime import datetime

from sqlmodel import Session

from app import crud
from app.core.config import settings
from app.db import engine, init_db
from app.models import BalanceSnapshotCreate, WalletCategory, WalletCreate
from app.services.registry import get_connector

SAMPLE_WALLETS = [
    WalletCreate(
        address="0xwalawalletalpha000000000000000000000001",
        label="WalaWallet Alpha",
        category=WalletCategory.exchange,
        provider="WalaWallet",
        network="Ethereum",
        verified=True,
        tags=["core", "custodial"],
        notes="Primary WalaWallet exchange account",
    ),
    WalletCreate(
        address="0xdormitprime00000000000000000000000003",
        label="Dormit Yield Vault",
        category=WalletCategory.defi,
        provider="Dormit",
        network="Polygon",
        verified=True,
        tags=["yield", "defi"],
        notes="Dormit vault used for staking rewards",
    ),
    WalletCreate(
        address="0xwicketstrategya0000000000000000000004",
        label="Wicket Validator",
        category=WalletCategory.treasury,
        provider="Wicket",
        network="Solana",
        verified=True,
        tags=["validator"],
        notes="Validator treasury to cover operations",
    ),
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        for wallet_in in SAMPLE_WALLETS:
            existing = crud.get_wallet_by_address(session, wallet_in.address)
            if existing:
                continue
            wallet = crud.create_wallet(session, wallet_in)
            connector = get_connector(wallet.provider)
            try:
                report = connector.fetch(wallet.address)
            except Exception as exc:  # pragma: no cover - convenience script
                print(f"Failed to fetch data for {wallet.address}: {exc}")
                continue
            snapshot_in = BalanceSnapshotCreate(
                wallet_id=wallet.id,
                captured_at=report.retrieved_at,
                native_symbol=report.native_symbol,
                native_balance=report.native_balance,
                total_usd=report.total_usd,
                source=connector.name,
                data=report.model_dump(),
            )
            crud.create_snapshot(session, snapshot_in)
    print("Seeded sample wallets.")


if __name__ == "__main__":
    seed()
