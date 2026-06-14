"""Wallet cross-reference helpers for litigation or investigation datasets.

The functions in this module do not ship with, verify, or assert any real-world
lawsuit allegations. They provide a neutral way to compare wallet identifiers
from one source (for example, a complaint, exhibit, or discovery production)
against a user's independently maintained known-wallet list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class WalletRecord:
    """A normalized wallet entry from either a reference source or user list."""

    wallet: str
    source: str = "unknown"
    label: str = ""
    notes: str = ""


@dataclass(frozen=True)
class WalletMatch:
    """A wallet appearing in both the reference list and the user's known list."""

    wallet: str
    reference_sources: tuple[str, ...]
    known_sources: tuple[str, ...]
    reference_labels: tuple[str, ...]
    known_labels: tuple[str, ...]
    reference_notes: tuple[str, ...]
    known_notes: tuple[str, ...]


def normalize_wallet(wallet: str) -> str:
    """Normalize a wallet identifier for deterministic comparisons.

    This keeps the comparison intentionally conservative: it trims whitespace
    and lowercases the value, but it does not try to infer chain-specific
    checksum variants or aliases.
    """
    normalized = str(wallet).strip().lower()
    if not normalized:
        raise ValueError("wallet cannot be blank")
    return normalized


def _coerce_record(record: WalletRecord | str, default_source: str) -> WalletRecord:
    if isinstance(record, WalletRecord):
        return WalletRecord(
            wallet=normalize_wallet(record.wallet),
            source=record.source or default_source,
            label=record.label,
            notes=record.notes,
        )
    return WalletRecord(wallet=normalize_wallet(record), source=default_source)


def _group_records(
    records: Iterable[WalletRecord | str],
    *,
    default_source: str,
) -> dict[str, list[WalletRecord]]:
    grouped: dict[str, list[WalletRecord]] = {}
    for record in records:
        coerced = _coerce_record(record, default_source)
        grouped.setdefault(coerced.wallet, []).append(coerced)
    return grouped


def cross_reference_wallets(
    reference_wallets: Iterable[WalletRecord | str],
    known_wallets: Iterable[WalletRecord | str],
    *,
    reference_source: str = "reference",
    known_source: str = "known",
) -> list[WalletMatch]:
    """Find wallets that appear in both a reference list and known-wallet list.

    Args:
        reference_wallets: Wallets from a complaint, exhibit, spreadsheet, or
            other outside reference. For example, this can represent the wallets
            described in a lawsuit, including a large set such as 39,000 rows.
        known_wallets: Wallets independently known by the user.
        reference_source: Fallback source name for plain-string reference rows.
        known_source: Fallback source name for plain-string known-wallet rows.

    Returns:
        Sorted wallet matches with source, label, and note context preserved.
    """
    references = _group_records(reference_wallets, default_source=reference_source)
    known = _group_records(known_wallets, default_source=known_source)

    matches: list[WalletMatch] = []
    for wallet in sorted(set(references) & set(known)):
        reference_records = references[wallet]
        known_records = known[wallet]
        matches.append(
            WalletMatch(
                wallet=wallet,
                reference_sources=tuple(sorted({item.source for item in reference_records})),
                known_sources=tuple(sorted({item.source for item in known_records})),
                reference_labels=tuple(item.label for item in reference_records if item.label),
                known_labels=tuple(item.label for item in known_records if item.label),
                reference_notes=tuple(item.notes for item in reference_records if item.notes),
                known_notes=tuple(item.notes for item in known_records if item.notes),
            )
        )
    return matches


def summarize_wallet_cross_reference(
    reference_wallets: Iterable[WalletRecord | str],
    known_wallets: Iterable[WalletRecord | str],
    *,
    reference_source: str = "reference",
    known_source: str = "known",
) -> dict[str, int | list[str]]:
    """Return counts and matched wallet IDs for a cross-reference run."""
    reference_list = list(reference_wallets)
    known_list = list(known_wallets)
    matches = cross_reference_wallets(
        reference_list,
        known_list,
        reference_source=reference_source,
        known_source=known_source,
    )
    return {
        "reference_wallet_count": len(reference_list),
        "known_wallet_count": len(known_list),
        "match_count": len(matches),
        "matched_wallets": [match.wallet for match in matches],
    }
