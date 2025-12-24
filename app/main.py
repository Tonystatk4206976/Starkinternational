from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from . import crud
from .db import get_session, init_db
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
from .services.errors import BalanceProviderError
from .services.refresh import refresh_wallet_balance

app = FastAPI(title="Wallet Aggregator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health", tags=["system"])
def health_check() -> dict:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/wallets", response_model=WalletRead, status_code=status.HTTP_201_CREATED)
def create_wallet_endpoint(wallet_in: WalletCreate, session: Session = Depends(get_session)) -> Wallet:
    existing = crud.get_wallet_by_address(session, wallet_in.address)
    if existing:
        raise HTTPException(status_code=409, detail="Wallet with this address already exists")
    wallet = crud.create_wallet(session, wallet_in)
    return wallet


@app.get("/wallets", response_model=List[WalletRead])
def list_wallets_endpoint(
    provider: Optional[str] = None,
    category: Optional[WalletCategory] = Query(default=None),
    verified: Optional[bool] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    session: Session = Depends(get_session),
) -> List[Wallet]:
    wallets = crud.list_wallets(
        session, provider=provider, category=category, verified=verified, tag=tag
    )
    for wallet in wallets:
        latest_snapshot = crud.get_latest_snapshot(session, wallet.id)
        if latest_snapshot:
            wallet.latest_snapshot = latest_snapshot  # type: ignore[attr-defined]
    return wallets


@app.get("/wallets/{wallet_id}", response_model=WalletRead)
def get_wallet_endpoint(wallet_id: int, session: Session = Depends(get_session)) -> Wallet:
    wallet = crud.get_wallet(session, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    latest_snapshot = crud.get_latest_snapshot(session, wallet_id)
    if latest_snapshot:
        wallet.latest_snapshot = latest_snapshot  # type: ignore[attr-defined]
    return wallet


@app.patch("/wallets/{wallet_id}", response_model=WalletRead)
def update_wallet_endpoint(
    wallet_id: int,
    wallet_update: WalletUpdate,
    session: Session = Depends(get_session),
) -> Wallet:
    wallet = crud.get_wallet(session, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    wallet = crud.update_wallet(session, wallet, wallet_update)
    return wallet


@app.delete("/wallets/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_wallet_endpoint(wallet_id: int, session: Session = Depends(get_session)) -> None:
    wallet = crud.get_wallet(session, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    crud.delete_wallet(session, wallet)


@app.get("/wallets/{wallet_id}/snapshots", response_model=List[BalanceSnapshotRead])
def list_snapshots_endpoint(wallet_id: int, session: Session = Depends(get_session)) -> List[BalanceSnapshot]:
    wallet = crud.get_wallet(session, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return crud.list_snapshots(session, wallet_id)


@app.post("/wallets/{wallet_id}/snapshots", response_model=BalanceSnapshotRead, status_code=status.HTTP_201_CREATED)
def create_snapshot_endpoint(
    wallet_id: int,
    snapshot_in: BalanceSnapshotCreate,
    session: Session = Depends(get_session),
) -> BalanceSnapshot:
    wallet = crud.get_wallet(session, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    if snapshot_in.wallet_id != wallet_id:
        raise HTTPException(status_code=400, detail="Wallet id mismatch")
    return crud.create_snapshot(session, snapshot_in)


@app.post("/wallets/{wallet_id}/refresh", response_model=BalanceSnapshotRead)
def refresh_wallet_endpoint(wallet_id: int, session: Session = Depends(get_session)) -> BalanceSnapshot:
    wallet = crud.get_wallet(session, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    try:
        snapshot = refresh_wallet_balance(session, wallet)
    except BalanceProviderError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error
    return snapshot


@app.get("/reports/summary")
def summary_report_endpoint(session: Session = Depends(get_session)) -> dict:
    wallets = crud.list_wallets(session)
    totals = {
        "overall_usd": 0.0,
        "by_provider": {},
        "by_category": {},
    }

    for wallet in wallets:
        latest = crud.get_latest_snapshot(session, wallet.id)
        if not latest:
            continue
        totals["overall_usd"] += latest.total_usd
        totals["by_provider"].setdefault(wallet.provider, 0.0)
        totals["by_provider"][wallet.provider] += latest.total_usd
        totals["by_category"].setdefault(wallet.category.value, 0.0)
        totals["by_category"][wallet.category.value] += latest.total_usd

    totals["last_updated"] = datetime.utcnow().isoformat()
    return totals
