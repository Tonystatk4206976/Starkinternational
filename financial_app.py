"""Secure personal-finance aggregation primitives.

This module intentionally avoids collecting cloud passwords, OAuth tokens, crypto
seed phrases, or private keys. It is a safe foundation for a financial app that
can ingest user-authorized exports from cloud storage providers, track crypto
wallets by public address only, and show what assets someone owns alongside who
manages each asset.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping

SUPPORTED_CLOUD_PROVIDERS = ("google_drive", "onedrive", "dropbox")
SUPPORTED_TRANSACTION_EXTENSIONS = {".csv", ".json"}
SUPPORTED_ASSET_EXTENSIONS = (".assets.csv", ".assets.json")

_PRIVATE_KEY_PATTERNS = (
    re.compile(r"\b0x[a-fA-F0-9]{64}\b"),
    re.compile(r"\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b"),
    re.compile(r"\b(xprv|yprv|zprv)[1-9A-HJ-NP-Za-km-z]{100,}\b", re.IGNORECASE),
)
_SEED_WORD_PATTERN = re.compile(r"\b([a-z]+\s+){11,23}[a-z]+\b", re.IGNORECASE)
_ADDRESS_PATTERN = re.compile(
    r"^(0x[a-fA-F0-9]{40}|bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$"
)


@dataclass(frozen=True)
class CloudSource:
    """A user-authorized source folder synced from a cloud provider."""

    provider: str
    root_path: Path

    def __post_init__(self) -> None:
        if self.provider not in SUPPORTED_CLOUD_PROVIDERS:
            providers = ", ".join(SUPPORTED_CLOUD_PROVIDERS)
            raise ValueError(f"provider must be one of: {providers}")
        object.__setattr__(self, "root_path", Path(self.root_path).expanduser())


@dataclass(frozen=True)
class Transaction:
    """Normalized transaction record imported from a financial document."""

    posted_at: date
    description: str
    amount: Decimal
    currency: str = "USD"
    account: str = "Unknown"
    category: str = "Uncategorized"
    source_provider: str = "manual"
    source_file: str = ""


@dataclass(frozen=True)
class AssetManager:
    """The person, institution, app, or wallet responsible for an asset."""

    name: str
    manager_type: str = "self"
    contact: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("manager name is required")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "manager_type", (self.manager_type or "self").strip().lower())
        object.__setattr__(self, "contact", self.contact.strip())


@dataclass(frozen=True)
class AssetHolding:
    """A normalized asset position and the manager responsible for it."""

    name: str
    asset_type: str
    quantity: Decimal
    value: Decimal
    currency: str = "USD"
    manager: AssetManager = field(default_factory=lambda: AssetManager("Self", "self"))
    account: str = "Unknown"
    source_provider: str = "manual"
    source_file: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("asset name is required")
        if self.quantity < 0:
            raise ValueError("asset quantity cannot be negative")
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "asset_type", (self.asset_type or "other").strip().lower())
        object.__setattr__(self, "currency", (self.currency or "USD").strip().upper())
        object.__setattr__(self, "account", (self.account or "Unknown").strip())


@dataclass(frozen=True)
class ManagedAssetView:
    """Dashboard row that answers: what do I own, what is it worth, who manages it?"""

    asset_name: str
    asset_type: str
    quantity: Decimal
    value: Decimal
    currency: str
    account: str
    manager_name: str
    manager_type: str
    source_provider: str


@dataclass(frozen=True)
class WalletReference:
    """Public, non-custodial reference to a crypto wallet."""

    label: str
    chain: str
    address: str
    manager: AssetManager = field(default_factory=lambda: AssetManager("Self", "self"))

    def __post_init__(self) -> None:
        reject_secret_material(self.address)
        if not _ADDRESS_PATTERN.match(self.address):
            raise ValueError("address must be a public Bitcoin or EVM-compatible address")

    def as_asset_holding(self, value: Decimal = Decimal("0"), currency: str = "USD") -> AssetHolding:
        """Represent the wallet itself in the unified assets view."""
        return AssetHolding(
            name=f"{self.chain.title()} wallet: {self.label}",
            asset_type="crypto_wallet",
            quantity=Decimal("1"),
            value=value,
            currency=currency,
            manager=self.manager,
            account=self.address,
            source_provider="wallet",
        )


@dataclass
class FinancialProfile:
    """A combined view of imported transactions, assets, and registered wallets."""

    transactions: list[Transaction] = field(default_factory=list)
    wallets: list[WalletReference] = field(default_factory=list)
    assets: list[AssetHolding] = field(default_factory=list)

    def add_transactions(self, transactions: Iterable[Transaction]) -> None:
        self.transactions.extend(transactions)

    def add_wallet(self, wallet: WalletReference) -> None:
        self.wallets.append(wallet)

    def add_assets(self, assets: Iterable[AssetHolding]) -> None:
        self.assets.extend(assets)

    def spending_by_category(self) -> dict[str, Decimal]:
        """Return positive spend totals grouped by category."""
        totals: dict[str, Decimal] = {}
        for transaction in self.transactions:
            if transaction.amount >= 0:
                continue
            totals[transaction.category] = totals.get(transaction.category, Decimal("0")) + abs(
                transaction.amount
            )
        return totals

    def net_cashflow(self, currency: str = "USD") -> Decimal:
        """Return net cashflow for one currency."""
        return sum(
            (transaction.amount for transaction in self.transactions if transaction.currency == currency),
            Decimal("0"),
        )

    def total_assets(self, currency: str = "USD") -> Decimal:
        """Return total known asset value for one currency."""
        return sum(
            (asset.value for asset in self.assets if asset.currency == currency),
            Decimal("0"),
        )

    def assets_by_manager(self, currency: str = "USD") -> dict[str, Decimal]:
        """Return known asset values grouped by manager for one currency."""
        totals: dict[str, Decimal] = {}
        for asset in self.assets:
            if asset.currency != currency:
                continue
            totals[asset.manager.name] = totals.get(asset.manager.name, Decimal("0")) + asset.value
        return totals

    def unified_asset_view(self, include_wallets: bool = True) -> list[ManagedAssetView]:
        """Return dashboard rows showing owned assets and who manages each one."""
        holdings = list(self.assets)
        if include_wallets:
            holdings.extend(wallet.as_asset_holding() for wallet in self.wallets)
        return [
            ManagedAssetView(
                asset_name=holding.name,
                asset_type=holding.asset_type,
                quantity=holding.quantity,
                value=holding.value,
                currency=holding.currency,
                account=holding.account,
                manager_name=holding.manager.name,
                manager_type=holding.manager.manager_type,
                source_provider=holding.source_provider,
            )
            for holding in sorted(
                holdings,
                key=lambda item: (item.manager.name.lower(), item.asset_type, item.name.lower()),
            )
        ]


class CloudDocumentImporter:
    """Import normalized financial documents from authorized cloud folders.

    The importer expects the user to connect cloud providers through their own
    approved sync clients or future OAuth screens, then points this class at the
    local synced folder. That keeps secrets out of the codebase.
    """

    def __init__(self, sources: Iterable[CloudSource]) -> None:
        self.sources = list(sources)

    def discover_documents(self) -> list[Path]:
        """Find supported financial export files under configured sources."""
        documents: list[Path] = []
        for source in self.sources:
            if not source.root_path.exists():
                continue
            for path in source.root_path.rglob("*"):
                if path.is_file() and _is_supported_document(path):
                    documents.append(path)
        return sorted(documents)

    def import_transactions(self) -> list[Transaction]:
        """Load transactions from every supported transaction document."""
        transactions: list[Transaction] = []
        for source in self.sources:
            if not source.root_path.exists():
                continue
            for path in sorted(source.root_path.rglob("*")):
                if not path.is_file() or not _is_transaction_document(path):
                    continue
                transactions.extend(_load_transactions(path, source.provider))
        return transactions

    def import_assets(self) -> list[AssetHolding]:
        """Load asset holdings from every supported asset document."""
        assets: list[AssetHolding] = []
        for source in self.sources:
            if not source.root_path.exists():
                continue
            for path in sorted(source.root_path.rglob("*")):
                if not path.is_file() or not _is_asset_document(path):
                    continue
                assets.extend(_load_assets(path, source.provider))
        return assets


def reject_secret_material(value: str) -> None:
    """Reject likely wallet secrets before they can be persisted or processed."""
    candidate = value.strip()
    for pattern in _PRIVATE_KEY_PATTERNS:
        if pattern.search(candidate):
            raise ValueError("wallet private keys or extended private keys are not accepted")
    words = candidate.split()
    if 12 <= len(words) <= 24 and _SEED_WORD_PATTERN.fullmatch(candidate):
        raise ValueError("seed phrases are not accepted; use public wallet addresses only")


def build_profile(
    sources: Iterable[CloudSource],
    wallets: Iterable[WalletReference],
    assets: Iterable[AssetHolding] = (),
) -> FinancialProfile:
    """Build a profile from user-authorized cloud exports, assets, and public wallets."""
    importer = CloudDocumentImporter(sources)
    profile = FinancialProfile()
    profile.add_transactions(importer.import_transactions())
    profile.add_assets(importer.import_assets())
    profile.add_assets(assets)
    for wallet in wallets:
        profile.add_wallet(wallet)
    return profile


def profile_fingerprint(profile: FinancialProfile) -> str:
    """Create a stable non-sensitive fingerprint useful for deduping sync runs."""
    payload = {
        "transactions": [
            {
                "posted_at": transaction.posted_at.isoformat(),
                "description": transaction.description,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "account": transaction.account,
                "category": transaction.category,
                "source_provider": transaction.source_provider,
                "source_file": transaction.source_file,
            }
            for transaction in sorted(
                profile.transactions,
                key=lambda item: (
                    item.posted_at,
                    item.description,
                    item.amount,
                    item.source_provider,
                    item.source_file,
                ),
            )
        ],
        "assets": [
            _asset_payload(asset)
            for asset in sorted(
                profile.assets,
                key=lambda item: (
                    item.manager.name,
                    item.asset_type,
                    item.name,
                    item.account,
                    item.source_provider,
                ),
            )
        ],
        "wallets": [
            {
                "label": wallet.label,
                "chain": wallet.chain,
                "address": wallet.address,
                "manager": _manager_payload(wallet.manager),
            }
            for wallet in sorted(profile.wallets, key=lambda item: item.address)
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_transactions(path: Path, source_provider: str) -> list[Transaction]:
    if path.suffix.lower() == ".csv":
        return _load_csv_transactions(path, source_provider)
    if path.suffix.lower() == ".json":
        return _load_json_transactions(path, source_provider)
    return []


def _load_csv_transactions(path: Path, source_provider: str) -> list[Transaction]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            _transaction_from_mapping(row, source_provider, str(path))
            for row in csv.DictReader(handle)
            if any(row.values())
        ]


def _load_json_transactions(path: Path, source_provider: str) -> list[Transaction]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload.get("transactions", payload) if isinstance(payload, Mapping) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a list of transactions")
    return [_transaction_from_mapping(row, source_provider, str(path)) for row in rows]


def _load_assets(path: Path, source_provider: str) -> list[AssetHolding]:
    if path.name.lower().endswith(".assets.csv"):
        return _load_csv_assets(path, source_provider)
    if path.name.lower().endswith(".assets.json"):
        return _load_json_assets(path, source_provider)
    return []


def _load_csv_assets(path: Path, source_provider: str) -> list[AssetHolding]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            _asset_from_mapping(row, source_provider, str(path))
            for row in csv.DictReader(handle)
            if any(row.values())
        ]


def _load_json_assets(path: Path, source_provider: str) -> list[AssetHolding]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    rows = payload.get("assets", payload) if isinstance(payload, Mapping) else payload
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a list of assets")
    return [_asset_from_mapping(row, source_provider, str(path)) for row in rows]


def _transaction_from_mapping(
    row: Mapping[str, object], source_provider: str, source_file: str
) -> Transaction:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    posted_at = _parse_date(_first_value(normalized, "date", "posted_at", "transaction_date"))
    amount = _parse_decimal(_first_value(normalized, "amount", "value", "total"))
    description = str(_first_value(normalized, "description", "memo", "name") or "").strip()
    if not description:
        raise ValueError(f"transaction in {source_file} is missing a description")
    return Transaction(
        posted_at=posted_at,
        description=description,
        amount=amount,
        currency=str(_first_value(normalized, "currency") or "USD").strip().upper(),
        account=str(_first_value(normalized, "account", "account_name") or "Unknown").strip(),
        category=str(_first_value(normalized, "category") or "Uncategorized").strip(),
        source_provider=source_provider,
        source_file=source_file,
    )


def _asset_from_mapping(row: Mapping[str, object], source_provider: str, source_file: str) -> AssetHolding:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    name = str(_first_value(normalized, "asset", "asset_name", "name", "symbol") or "").strip()
    if not name:
        raise ValueError(f"asset in {source_file} is missing a name")
    manager_name = str(
        _first_value(normalized, "manager", "manager_name", "custodian", "advisor", "exchange") or "Self"
    ).strip()
    manager = AssetManager(
        name=manager_name,
        manager_type=str(_first_value(normalized, "manager_type", "custodian_type") or "self"),
        contact=str(_first_value(normalized, "manager_contact", "contact") or ""),
    )
    return AssetHolding(
        name=name,
        asset_type=str(_first_value(normalized, "asset_type", "type", "class") or "other"),
        quantity=_parse_decimal(_first_value(normalized, "quantity", "shares", "units", "balance") or "0"),
        value=_parse_decimal(_first_value(normalized, "value", "market_value", "current_value", "total") or "0"),
        currency=str(_first_value(normalized, "currency") or "USD"),
        manager=manager,
        account=str(_first_value(normalized, "account", "account_name", "wallet", "address") or "Unknown"),
        source_provider=source_provider,
        source_file=source_file,
    )


def _asset_payload(asset: AssetHolding) -> dict[str, object]:
    return {
        "name": asset.name,
        "asset_type": asset.asset_type,
        "quantity": str(asset.quantity),
        "value": str(asset.value),
        "currency": asset.currency,
        "account": asset.account,
        "manager": _manager_payload(asset.manager),
        "source_provider": asset.source_provider,
        "source_file": asset.source_file,
    }


def _manager_payload(manager: AssetManager) -> dict[str, str]:
    return {
        "name": manager.name,
        "manager_type": manager.manager_type,
        "contact": manager.contact,
    }


def _is_supported_document(path: Path) -> bool:
    return _is_transaction_document(path) or _is_asset_document(path)


def _is_transaction_document(path: Path) -> bool:
    name = path.name.lower()
    return path.suffix.lower() in SUPPORTED_TRANSACTION_EXTENSIONS and not name.endswith(SUPPORTED_ASSET_EXTENSIONS)


def _is_asset_document(path: Path) -> bool:
    return path.name.lower().endswith(SUPPORTED_ASSET_EXTENSIONS)


def _first_value(row: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _parse_date(value: object | None) -> date:
    if value is None:
        raise ValueError("transaction is missing a date")
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    for date_format in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    raise ValueError(f"unsupported transaction date: {value!r}")


def _parse_decimal(value: object | None) -> Decimal:
    if value is None:
        raise ValueError("transaction is missing an amount")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"unsupported transaction amount: {value!r}") from exc
