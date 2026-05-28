"""Secure personal-finance aggregation primitives.

This module intentionally avoids collecting cloud passwords, OAuth tokens, crypto
seed phrases, or private keys. It is a safe foundation for a financial app that
can ingest user-authorized exports from cloud storage providers and track crypto
wallets by public address only.
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
class WalletReference:
    """Public, non-custodial reference to a crypto wallet."""

    label: str
    chain: str
    address: str

    def __post_init__(self) -> None:
        reject_secret_material(self.address)
        if not _ADDRESS_PATTERN.match(self.address):
            raise ValueError("address must be a public Bitcoin or EVM-compatible address")


@dataclass
class FinancialProfile:
    """A combined view of imported transactions and registered wallets."""

    transactions: list[Transaction] = field(default_factory=list)
    wallets: list[WalletReference] = field(default_factory=list)

    def add_transactions(self, transactions: Iterable[Transaction]) -> None:
        self.transactions.extend(transactions)

    def add_wallet(self, wallet: WalletReference) -> None:
        self.wallets.append(wallet)

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


class CloudDocumentImporter:
    """Import normalized transaction documents from authorized cloud folders.

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
                if path.is_file() and path.suffix.lower() in SUPPORTED_TRANSACTION_EXTENSIONS:
                    documents.append(path)
        return sorted(documents)

    def import_transactions(self) -> list[Transaction]:
        """Load transactions from every supported document in every source."""
        transactions: list[Transaction] = []
        for source in self.sources:
            if not source.root_path.exists():
                continue
            for path in sorted(source.root_path.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in SUPPORTED_TRANSACTION_EXTENSIONS:
                    continue
                transactions.extend(_load_transactions(path, source.provider))
        return transactions


def reject_secret_material(value: str) -> None:
    """Reject likely wallet secrets before they can be persisted or processed."""
    candidate = value.strip()
    for pattern in _PRIVATE_KEY_PATTERNS:
        if pattern.search(candidate):
            raise ValueError("wallet private keys or extended private keys are not accepted")
    words = candidate.split()
    if 12 <= len(words) <= 24 and _SEED_WORD_PATTERN.fullmatch(candidate):
        raise ValueError("seed phrases are not accepted; use public wallet addresses only")


def build_profile(sources: Iterable[CloudSource], wallets: Iterable[WalletReference]) -> FinancialProfile:
    """Build a profile from user-authorized cloud exports and public wallets."""
    profile = FinancialProfile()
    profile.add_transactions(CloudDocumentImporter(sources).import_transactions())
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
        "wallets": [wallet.__dict__ for wallet in sorted(profile.wallets, key=lambda item: item.address)],
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
