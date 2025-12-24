from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, JSON, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel


class WalletCategory(str, Enum):
    exchange = "exchange"
    defi = "defi"
    treasury = "treasury"
    other = "other"


class WalletBase(SQLModel):
    address: str = Field(index=True, description="Public address of the wallet.")
    label: Optional[str] = Field(default=None, description="Friendly name for the wallet.")
    category: WalletCategory = Field(default=WalletCategory.other, description="Wallet classification.")
    provider: str = Field(description="Originating provider such as WalaWallet or Dormit.")
    network: Optional[str] = Field(default=None, description="Underlying network (Ethereum, Solana, etc.).")
    verified: bool = Field(default=False, description="True when the wallet has been verified by the exchange or DeFi protocol.")
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, default=list),
        description="Arbitrary tags used for grouping wallets.",
    )
    notes: Optional[str] = Field(default=None, description="Additional information about the wallet.")


class Wallet(WalletBase, table=True):
    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("address", name="uq_wallet_address"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    snapshots: List["BalanceSnapshot"] = Relationship(back_populates="wallet")


class WalletCreate(WalletBase):
    pass


class WalletUpdate(SQLModel):
    label: Optional[str] = None
    category: Optional[WalletCategory] = None
    provider: Optional[str] = None
    network: Optional[str] = None
    verified: Optional[bool] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class WalletRead(WalletBase):
    id: int
    created_at: datetime
    updated_at: datetime
    latest_snapshot: Optional["BalanceSnapshotRead"] = None


class TokenBalance(SQLModel):
    symbol: str
    amount: float
    usd_value: float
    contract_address: Optional[str] = None


class BalanceSnapshotBase(SQLModel):
    captured_at: datetime = Field(default_factory=datetime.utcnow, description="When the balance was captured.")
    native_symbol: str = Field(description="Symbol of the native asset for the network (ETH, SOL, etc.).")
    native_balance: float = Field(description="Quantity of the native asset held by the wallet.")
    total_usd: float = Field(description="Total USD valuation of the wallet at capture time.")
    source: str = Field(description="Connector or provider that supplied the balances.")
    data: dict = Field(default_factory=dict, sa_column=Column(JSON, default=dict))


class BalanceSnapshot(BalanceSnapshotBase, table=True):
    __tablename__ = "balance_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    wallet_id: int = Field(foreign_key="wallets.id", index=True, nullable=False)

    wallet: Wallet = Relationship(back_populates="snapshots")


class BalanceSnapshotCreate(BalanceSnapshotBase):
    wallet_id: int


class BalanceSnapshotRead(BalanceSnapshotBase):
    id: int
    wallet_id: int
