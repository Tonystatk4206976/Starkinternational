from datetime import datetime

from sqlmodel import Session

from .. import crud
from ..models import BalanceSnapshotCreate, Wallet
from .errors import BalanceProviderError
from .registry import get_connector


def refresh_wallet_balance(session: Session, wallet: Wallet):
    """Fetch the latest balance for the wallet and persist a snapshot."""
    connector = get_connector(wallet.provider)
    report = connector.fetch(wallet.address)

    snapshot_in = BalanceSnapshotCreate(
        wallet_id=wallet.id,
        captured_at=report.retrieved_at,
        native_symbol=report.native_symbol,
        native_balance=report.native_balance,
        total_usd=report.total_usd,
        source=connector.name,
        data=report.model_dump(),
    )

    snapshot = crud.create_snapshot(session, snapshot_in)
    wallet.updated_at = datetime.utcnow()
    session.add(wallet)
    session.commit()
    session.refresh(wallet)
    return snapshot
