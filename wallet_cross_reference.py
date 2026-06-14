"""Wallet cross-reference helpers for legal and audit review workflows.

The functions in this module intentionally avoid external dependencies so they
can be used from lightweight dashboards, notebooks, or document-prep scripts.
They normalize wallet strings, group matching references, and produce concise
review notes that can be attached to case files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


WalletRecord = Mapping[str, object]


@dataclass(frozen=True)
class WalletReference:
    """A single occurrence of a wallet address in source material."""

    wallet: str
    source: str
    label: str = ""
    note: str = ""


@dataclass(frozen=True)
class WalletCrossReference:
    """Grouped references for one normalized wallet address."""

    wallet: str
    references: tuple[WalletReference, ...]

    @property
    def source_count(self) -> int:
        """Return the number of distinct sources mentioning the wallet."""
        return len({reference.source for reference in self.references})

    @property
    def labels(self) -> tuple[str, ...]:
        """Return unique non-empty labels associated with the wallet."""
        return tuple(
            sorted({reference.label for reference in self.references if reference.label})
        )


def normalize_wallet_address(wallet: object) -> str:
    """Normalize a wallet address for consistent cross-reference matching.

    The helper trims whitespace, removes internal spacing sometimes introduced
    by copied legal exhibits, and lowercases the result. A blank value is not a
    usable address and raises ``ValueError``.
    """
    normalized = "".join(str(wallet).strip().split()).lower()
    if not normalized:
        raise ValueError("wallet address cannot be blank")
    return normalized


def build_wallet_references(records: Iterable[WalletRecord]) -> tuple[WalletReference, ...]:
    """Convert dictionaries into validated ``WalletReference`` objects.

    Expected record keys are ``wallet`` and ``source``. Optional keys are
    ``label`` and ``note``. Keeping the input shape dictionary-based makes the
    helper easy to feed from CSV rows, JSON exports, and spreadsheet adapters.
    """
    references: list[WalletReference] = []
    for index, record in enumerate(records, start=1):
        wallet = normalize_wallet_address(record.get("wallet", ""))
        source = str(record.get("source", "")).strip()
        if not source:
            raise ValueError(f"record {index} is missing a source")

        references.append(
            WalletReference(
                wallet=wallet,
                source=source,
                label=str(record.get("label", "")).strip(),
                note=str(record.get("note", "")).strip(),
            )
        )
    return tuple(references)


def cross_reference_wallets(
    records: Iterable[WalletRecord],
    *,
    minimum_sources: int = 2,
) -> tuple[WalletCrossReference, ...]:
    """Group wallets that appear across at least ``minimum_sources`` sources.

    Args:
        records: Iterable of wallet reference dictionaries.
        minimum_sources: Minimum number of distinct sources required before a
            wallet is included in the result. Use ``1`` to include every wallet.

    Returns:
        Cross-reference groups sorted by strongest source coverage first, then
        wallet address for deterministic reports.
    """
    if minimum_sources < 1:
        raise ValueError("minimum_sources must be at least 1")

    grouped: dict[str, list[WalletReference]] = {}
    for reference in build_wallet_references(records):
        grouped.setdefault(reference.wallet, []).append(reference)

    matches = [
        WalletCrossReference(wallet=wallet, references=tuple(references))
        for wallet, references in grouped.items()
        if len({reference.source for reference in references}) >= minimum_sources
    ]
    return tuple(sorted(matches, key=lambda item: (-item.source_count, item.wallet)))


def format_wallet_cross_reference_report(
    cross_references: Sequence[WalletCrossReference],
) -> list[str]:
    """Format cross-reference groups as concise human-readable bullets."""
    report: list[str] = []
    for match in cross_references:
        sources = ", ".join(
            sorted({reference.source for reference in match.references})
        )
        labels = f" | labels: {', '.join(match.labels)}" if match.labels else ""
        report.append(
            f"{match.wallet} — {match.source_count} source(s): {sources}{labels}"
        )
    return report
