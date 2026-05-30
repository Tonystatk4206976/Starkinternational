"""Helpers for combining public GitHub activity from multiple accounts."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

GITHUB_EVENTS_URL = "https://api.github.com/users/{username}/events/public"


@dataclass(frozen=True)
class GitHubActivityEvent:
    """Normalized public GitHub activity event.

    Attributes:
        account: GitHub account whose event feed contained the event.
        event_id: GitHub event identifier.
        event_type: GitHub event type, such as ``PushEvent`` or ``IssuesEvent``.
        repo: Repository name in ``owner/repo`` form when available.
        actor: Actor login attached to the event.
        created_at: Event timestamp as a timezone-aware UTC datetime.
        payload: Event payload returned by the GitHub API.
        raw: Original event mapping returned by the GitHub API.
    """

    account: str
    event_id: str
    event_type: str
    repo: str | None
    actor: str | None
    created_at: datetime
    payload: Mapping[str, Any]
    raw: Mapping[str, Any]


def _parse_github_timestamp(value: str) -> datetime:
    """Parse GitHub's ISO-8601 timestamp as a timezone-aware UTC datetime."""
    if not value:
        raise ValueError("GitHub event is missing created_at")

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normalize_github_event(account: str, event: Mapping[str, Any]) -> GitHubActivityEvent:
    """Convert one GitHub public-event mapping into a normalized event object."""
    event_id = str(event.get("id") or "")
    if not event_id:
        raise ValueError("GitHub event is missing id")

    repo_value = event.get("repo") or {}
    actor_value = event.get("actor") or {}
    payload = event.get("payload") or {}

    return GitHubActivityEvent(
        account=account,
        event_id=event_id,
        event_type=str(event.get("type") or "UnknownEvent"),
        repo=repo_value.get("name") if isinstance(repo_value, Mapping) else None,
        actor=actor_value.get("login") if isinstance(actor_value, Mapping) else None,
        created_at=_parse_github_timestamp(str(event.get("created_at") or "")),
        payload=payload if isinstance(payload, Mapping) else {},
        raw=event,
    )


def fetch_public_github_events(
    username: str,
    *,
    pages: int = 1,
    per_page: int = 100,
    token: str | None = None,
    timeout: float = 10.0,
) -> list[Mapping[str, Any]]:
    """Fetch public events for a GitHub account.

    Args:
        username: GitHub username to query.
        pages: Number of API result pages to fetch.
        per_page: Events per page. GitHub caps this endpoint at 100.
        token: Optional GitHub token for higher API rate limits.
        timeout: Request timeout in seconds.

    Returns:
        Raw event dictionaries from GitHub's public events API.
    """
    if not username.strip():
        raise ValueError("username is required")
    if pages < 1:
        raise ValueError("pages must be at least 1")
    if not 1 <= per_page <= 100:
        raise ValueError("per_page must be between 1 and 100")

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Starkinternational-GitHub-Activity-Merger",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    events: list[Mapping[str, Any]] = []
    safe_username = quote(username.strip(), safe="")
    for page in range(1, pages + 1):
        base_url = GITHUB_EVENTS_URL.format(username=safe_username)
        url = f"{base_url}?per_page={per_page}&page={page}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                page_events = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API request failed for {username}: {exc.code} {message}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"GitHub API request failed for {username}: {exc.reason}"
            ) from exc

        if not isinstance(page_events, list):
            raise RuntimeError(
                f"GitHub API returned an unexpected response for {username}"
            )
        if not page_events:
            break
        events.extend(page_events)

    return events


EventFetcher = Callable[[str], Iterable[Mapping[str, Any]]]


def merge_github_account_activity(
    accounts: Sequence[str],
    *,
    fetcher: EventFetcher | None = None,
    pages: int = 1,
    per_page: int = 100,
    token: str | None = None,
) -> list[GitHubActivityEvent]:
    """Merge public activity feeds for multiple GitHub accounts.

    Events are deduplicated by GitHub event id and sorted newest first. Provide a
    custom ``fetcher`` in tests or when reading cached API responses.
    """
    if not accounts:
        raise ValueError("at least one account is required")

    seen: set[str] = set()
    merged: list[GitHubActivityEvent] = []

    for account in accounts:
        clean_account = account.strip()
        if not clean_account:
            raise ValueError("account names cannot be blank")

        raw_events = (
            fetcher(clean_account)
            if fetcher is not None
            else fetch_public_github_events(
                clean_account, pages=pages, per_page=per_page, token=token
            )
        )
        for raw_event in raw_events:
            event = normalize_github_event(clean_account, raw_event)
            if event.event_id in seen:
                continue
            seen.add(event.event_id)
            merged.append(event)

    return sorted(merged, key=lambda event: event.created_at, reverse=True)


def summarize_activity_by_account(events: Iterable[GitHubActivityEvent]) -> dict[str, int]:
    """Count merged GitHub events by source account."""
    summary: dict[str, int] = {}
    for event in events:
        summary[event.account] = summary.get(event.account, 0) + 1
    return summary
