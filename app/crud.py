from datetime import datetime
from typing import List, Optional

from sqlmodel import Session, select

from .models import (
    BalanceSnapshot,
    BalanceSnapshotCreate,
    BalanceSnapshotRead,
    Wallet,
    WalletCategory,
    WalletCreate,
    WalletRead,
    WalletUpdate,
)


def create_wallet(session: Session, wallet_in: WalletCreate) -> Wallet:
    wallet = Wallet(**wallet_in.model_dump())
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


def update_wallet(session: Session, wallet: Wallet, wallet_update: WalletUpdate) -> Wallet:
    update_data = wallet_update.model_dump(exclude_unset=True)
    if not update_data:
        return wallet

    for field, value in update_data.items():
        setattr(wallet, field, value)
    wallet.updated_at = datetime.utcnow()
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return wallet


def delete_wallet(session: Session, wallet: Wallet) -> None:
    session.delete(wallet)
    session.commit()


def get_wallet(session: Session, wallet_id: int) -> Optional[Wallet]:
    return session.get(Wallet, wallet_id)


def get_wallet_by_address(session: Session, address: str) -> Optional[Wallet]:
    statement = select(Wallet).where(Wallet.address == address)
    return session.exec(statement).one_or_none()


def list_wallets(
    session: Session,
    provider: Optional[str] = None,
    category: Optional[WalletCategory] = None,
    verified: Optional[bool] = None,
    tag: Optional[str] = None,
) -> List[Wallet]:
    statement = select(Wallet)
    if provider:
        statement = statement.where(Wallet.provider == provider)
    if category:
        statement = statement.where(Wallet.category == category)
    if verified is not None:
        statement = statement.where(Wallet.verified == verified)
    statement = statement.order_by(Wallet.created_at.desc())
    wallets = list(session.exec(statement))
    if tag:
        wallets = [wallet for wallet in wallets if tag in (wallet.tags or [])]
    return wallets


def create_snapshot(session: Session, snapshot_in: BalanceSnapshotCreate) -> BalanceSnapshot:
    snapshot = BalanceSnapshot(**snapshot_in.model_dump())
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def list_snapshots(session: Session, wallet_id: int) -> List[BalanceSnapshot]:
    statement = (
        select(BalanceSnapshot)
        .where(BalanceSnapshot.wallet_id == wallet_id)
        .order_by(BalanceSnapshot.captured_at.desc())
    )
    return list(session.exec(statement))


def get_latest_snapshot(session: Session, wallet_id: int) -> Optional[BalanceSnapshot]:
    statement = (
        select(BalanceSnapshot)
        .where(BalanceSnapshot.wallet_id == wallet_id)
        .order_by(BalanceSnapshot.captured_at.desc())
        .limit(1)
    )
    return session.exec(statement).one_or_none()


def get_wallets_with_latest_snapshot(session: Session) -> List[Wallet]:
    wallets = list(session.exec(select(Wallet)))
    for wallet in wallets:
        latest = get_latest_snapshot(session, wallet.id)
        if latest:
            wallet.latest_snapshot = latest  # type: ignore[attr-defined]
        else:
            wallet.latest_snapshot = None  # type: ignore[attr-defined]
    return wallets
