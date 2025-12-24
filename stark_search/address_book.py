"""Utilities for managing address records and validating them via live APIs."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from typing import Iterable, List, Optional

from .indexer import initialize_database

__all__ = [
    "add_address",
    "list_addresses",
    "check_address_live",
]


def add_address(db_path: os.PathLike[str] | str | bytes, address: str) -> bool:
    """Store *address* in the database and return ``True`` when inserted.

    Existing rows are left untouched so the function returns ``False`` when the
    address is already present. Empty or whitespace-only addresses raise a
    :class:`ValueError`.
    """

    cleaned = address.strip()
    if not cleaned:
        raise ValueError("address must not be empty")

    conn = initialize_database(db_path)
    try:
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                INSERT INTO addresses(address)
                VALUES (?)
                ON CONFLICT(address) DO NOTHING
                """,
                (cleaned,),
            )
            conn.commit()
            return cursor.rowcount > 0
    finally:
        conn.close()


def list_addresses(db_path: os.PathLike[str] | str | bytes) -> List[dict]:
    """Return all stored addresses ordered by creation time (newest first)."""

    conn = initialize_database(db_path)
    conn.row_factory = sqlite_dict_factory
    try:
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                SELECT id, address, created_at
                FROM addresses
                ORDER BY datetime(created_at) DESC, id DESC
                """
            )
            return cursor.fetchall()
    finally:
        conn.close()


def check_address_live(
    address: str,
    *,
    endpoint: str,
    timeout: float = 10.0,
    extra_query: Optional[dict[str, str]] = None,
) -> dict:
    """Query a remote API endpoint to validate *address*.

    The *endpoint* must be a fully-qualified URL. The function issues a GET
    request with an ``address`` query parameter (plus any *extra_query*
    key/value pairs) and expects a JSON response. The decoded JSON is returned
    as a dictionary along with a normalized ``query_address`` field for
    convenience.
    """

    cleaned = address.strip()
    if not cleaned:
        raise ValueError("address must not be empty")

    url = _compose_lookup_url(endpoint, cleaned, extra_query or {})
    request = urllib.request.Request(url, headers={"Accept": "application/json"})

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.URLError as exc:  # pragma: no cover - network errors
        raise ConnectionError(f"Failed to query live database: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Endpoint did not return a JSON object")

    payload.setdefault("query_address", cleaned)
    return payload


def _compose_lookup_url(
    endpoint: str, address: str, extra_params: Iterable[tuple[str, str]] | dict[str, str]
) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("endpoint must be an absolute URL")

    if isinstance(extra_params, dict):
        params_iter = list(extra_params.items())
    else:
        params_iter = list(extra_params)

    normalized_params = [(str(key), str(value)) for key, value in params_iter]

    query_params = list(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    query_params.extend(normalized_params)
    query_params.append(("address", address))

    encoded_query = urllib.parse.urlencode(query_params)
    rebuilt = parsed._replace(query=encoded_query)
    return urllib.parse.urlunparse(rebuilt)


def sqlite_dict_factory(cursor, row):
    return {description[0]: value for description, value in zip(cursor.description, row)}

