"""Indexing and search utilities for building a local SQLite database.

The module exposes helpers to crawl a directory tree, capture file metadata,
and store the collected information in a SQLite database that supports
full-text search.  The resulting database can be queried via the
``search_database`` function or the command line interface in
:mod:`stark_search.cli`.

In addition to populating the search index, the module now keeps track of
notable events (missing files, permission changes, read errors, …) so that
callers can implement monitoring and alerting workflows on top of the
ingestion process.
"""

from __future__ import annotations

import fnmatch
import os
import pathlib
import sqlite3
import time
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence

__all__ = [
    "FileRecord",
    "initialize_database",
    "index_directory",
    "search_database",
    "fetch_recent_events",
    "add_address_record",
    "list_address_records",
]


@dataclass
class FileRecord:
    """Structured representation of a single file entry."""

    path: str
    name: str
    extension: str
    size: int
    mtime: float
    mode: int
    content: Optional[str]


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    """Add *column* to *table* if it does not already exist."""

    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})")
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def initialize_database(db_path: os.PathLike[str] | str) -> sqlite3.Connection:
    """Create the SQLite schema if necessary and return an open connection.

    Parameters
    ----------
    db_path:
        Location of the database file. The parent directory will be created if
        it does not already exist.
    """

    path = pathlib.Path(db_path)
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS files_metadata (
            path TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            extension TEXT,
            size INTEGER,
            mtime REAL,
            mode INTEGER
        )
        """
    )

    _ensure_column(conn, "files_metadata", "mode", "INTEGER")

    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS files_content USING fts5(
            path UNINDEXED,
            content,
            tokenize = 'porter'
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            type TEXT NOT NULL,
            path TEXT,
            details TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS addresses (
            address TEXT PRIMARY KEY,
            label TEXT,
            category TEXT,
            notes TEXT,
            added_at REAL NOT NULL,
            updated_at REAL NOT NULL
        )
        """
    )

    return conn


def _should_ignore(path: pathlib.Path, patterns: Sequence[str]) -> bool:
    if not patterns:
        return False

    path_str = str(path)
    return any(fnmatch.fnmatch(path_str, pattern) for pattern in patterns)


def _read_text_sample(
    path: pathlib.Path, max_bytes: int
) -> tuple[Optional[str], Optional[str]]:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(max_bytes)
    except OSError as exc:
        return None, f"Unable to read file: {exc}"

    if not chunk:
        return "", None

    try:
        return chunk.decode("utf-8"), None
    except UnicodeDecodeError:
        return chunk.decode("utf-8", errors="ignore"), None


def _record_event(
    conn: sqlite3.Connection,
    event_type: str,
    path: str,
    details: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO events(timestamp, type, path, details)
        VALUES(?, ?, ?, ?)
        """,
        (time.time(), event_type, path, details),
    )


def iter_files(
    root: os.PathLike[str] | str,
    *,
    follow_symlinks: bool = False,
    ignore_patterns: Optional[Sequence[str]] = None,
) -> Iterator[pathlib.Path]:
    """Yield files contained in *root* honoring ignore patterns."""

    root_path = pathlib.Path(root).resolve()
    patterns = ignore_patterns or []

    for dirpath, dirnames, filenames in os.walk(root_path, followlinks=follow_symlinks):
        dir_path = pathlib.Path(dirpath)
        dirnames[:] = [
            name
            for name in dirnames
            if not _should_ignore(dir_path / name, patterns)
        ]

        for filename in filenames:
            file_path = dir_path / filename
            if _should_ignore(file_path, patterns):
                continue
            yield file_path


def index_directory(
    root: os.PathLike[str] | str,
    db_path: os.PathLike[str] | str,
    *,
    follow_symlinks: bool = False,
    ignore_patterns: Optional[Sequence[str]] = None,
    max_content_bytes: int = 1_000_000,
) -> int:
    """Populate *db_path* with entries from *root* and return the count.

    Existing records for the same ``path`` are replaced to keep the database
    in sync with the file system.
    """

    conn = initialize_database(db_path)
    conn.execute("BEGIN")

    try:
        existing_records: Dict[str, dict[str, float | int | None]] = {
            row[0]: {"size": row[1], "mtime": row[2], "mode": row[3]}
            for row in conn.execute(
                "SELECT path, size, mtime, mode FROM files_metadata"
            )
        }

        count = 0
        for file_path in iter_files(
            root,
            follow_symlinks=follow_symlinks,
            ignore_patterns=ignore_patterns,
        ):
            try:
                stat = file_path.stat()
            except OSError as exc:
                _record_event(
                    conn,
                    "stat_error",
                    str(file_path),
                    f"Unable to stat file: {exc}",
                )
                continue
            mode = stat.st_mode & 0o777
            content, read_error = _read_text_sample(file_path, max_content_bytes)
            if read_error:
                _record_event(conn, "read_error", str(file_path), read_error)
            record = FileRecord(
                path=str(file_path),
                name=file_path.name,
                extension=file_path.suffix.lower().lstrip("."),
                size=stat.st_size,
                mtime=stat.st_mtime,
                mode=mode,
                content=content,
            )

            previous = existing_records.pop(record.path, None)
            previous_mode = previous.get("mode") if previous else None
            if previous_mode is not None and previous_mode != mode:
                _record_event(
                    conn,
                    "permission_change",
                    record.path,
                    f"Mode changed from {oct(previous_mode)} to {oct(mode)}",
                )

            conn.execute(
                """
                INSERT INTO files_metadata(path, name, extension, size, mtime, mode)
                VALUES(:path, :name, :extension, :size, :mtime, :mode)
                ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name,
                    extension=excluded.extension,
                    size=excluded.size,
                    mtime=excluded.mtime,
                    mode=excluded.mode
                """,
                {
                    "path": record.path,
                    "name": record.name,
                    "extension": record.extension,
                    "size": record.size,
                    "mtime": record.mtime,
                    "mode": record.mode,
                },
            )

            conn.execute(
                "DELETE FROM files_content WHERE path = ?",
                (record.path,),
            )
            conn.execute(
                "INSERT INTO files_content(path, content) VALUES(:path, :content)",
                {
                    "path": record.path,
                    "content": record.content or "",
                },
            )
            count += 1

        for missing_path, previous in existing_records.items():
            _record_event(
                conn,
                "missing_file",
                missing_path,
                "File previously indexed but now absent",
            )
            conn.execute(
                "DELETE FROM files_metadata WHERE path = ?",
                (missing_path,),
            )
            conn.execute(
                "DELETE FROM files_content WHERE path = ?",
                (missing_path,),
            )

        conn.commit()
        return count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def search_database(
    db_path: os.PathLike[str] | str,
    query: str,
    *,
    limit: int = 20,
) -> List[dict]:
    """Run an FTS5 query against the database and return matching rows."""

    conn = initialize_database(db_path)
    conn.row_factory = sqlite3.Row

    try:
        cursor = conn.execute(
            """
            SELECT m.path, m.name, m.extension, m.size, m.mtime,
                   snippet(files_content, 0, '[', ']', ' … ', 10) AS snippet,
                   bm25(files_content) AS score
            FROM files_content
            JOIN files_metadata AS m ON m.path = files_content.path
            WHERE files_content MATCH ?
            ORDER BY score ASC
            LIMIT ?
            """,
            (query, limit),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def fetch_recent_events(
    db_path: os.PathLike[str] | str,
    *,
    limit: int = 50,
) -> List[dict]:
    """Return at most *limit* most recent ingestion events."""

    conn = initialize_database(db_path)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute(
            """
            SELECT timestamp, type, path, details
            FROM events
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def add_address_record(
    db_path: os.PathLike[str] | str,
    address: str,
    *,
    label: str | None = None,
    category: str | None = None,
    notes: str | None = None,
) -> None:
    """Insert or update a tracked blockchain address in the database."""

    normalized = address.strip()
    if not normalized:
        raise ValueError("address must not be empty")

    timestamp = time.time()
    conn = initialize_database(db_path)

    try:
        conn.execute(
            """
            INSERT INTO addresses(address, label, category, notes, added_at, updated_at)
            VALUES(?, ?, ?, ?, ?, ?)
            ON CONFLICT(address) DO UPDATE SET
                label=excluded.label,
                category=COALESCE(excluded.category, addresses.category),
                notes=COALESCE(excluded.notes, addresses.notes),
                updated_at=excluded.updated_at
            """,
            (
                normalized,
                label,
                category,
                notes,
                timestamp,
                timestamp,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def list_address_records(
    db_path: os.PathLike[str] | str,
    *,
    category: str | None = None,
) -> List[dict]:
    """Return tracked blockchain addresses, optionally filtered by category."""

    conn = initialize_database(db_path)
    conn.row_factory = sqlite3.Row
    try:
        if category:
            cursor = conn.execute(
                """
                SELECT address, label, category, notes, added_at, updated_at
                FROM addresses
                WHERE category = ?
                ORDER BY updated_at DESC
                """,
                (category,),
            )
        else:
            cursor = conn.execute(
                """
                SELECT address, label, category, notes, added_at, updated_at
                FROM addresses
                ORDER BY updated_at DESC
                """
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
