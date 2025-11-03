"""Indexing and search utilities for building a local SQLite database.

The module exposes helpers to crawl a directory tree, capture file metadata,
and store the collected information in a SQLite database that supports
full-text search.  The resulting database can be queried via the
``search_database`` function or the command line interface in
:mod:`stark_search.cli`.
"""

from __future__ import annotations

import fnmatch
import os
import pathlib
import sqlite3
from dataclasses import dataclass
from typing import Iterator, List, Optional, Sequence

__all__ = [
    "FileRecord",
    "initialize_database",
    "index_directory",
    "search_database",
]


@dataclass
class FileRecord:
    """Structured representation of a single file entry."""

    path: str
    name: str
    extension: str
    size: int
    mtime: float
    content: Optional[str]


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
            mtime REAL
        )
        """
    )

    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS files_content USING fts5(
            path UNINDEXED,
            content,
            tokenize = 'porter'
        )
        """
    )

    return conn


def _should_ignore(path: pathlib.Path, patterns: Sequence[str]) -> bool:
    if not patterns:
        return False

    path_str = str(path)
    return any(fnmatch.fnmatch(path_str, pattern) for pattern in patterns)


def _read_text_sample(path: pathlib.Path, max_bytes: int) -> Optional[str]:
    try:
        with path.open("rb") as handle:
            chunk = handle.read(max_bytes)
    except OSError:
        return None

    if not chunk:
        return ""

    try:
        return chunk.decode("utf-8")
    except UnicodeDecodeError:
        return chunk.decode("utf-8", errors="ignore")


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
        count = 0
        for file_path in iter_files(
            root,
            follow_symlinks=follow_symlinks,
            ignore_patterns=ignore_patterns,
        ):
            stat = file_path.stat()
            record = FileRecord(
                path=str(file_path),
                name=file_path.name,
                extension=file_path.suffix.lower().lstrip("."),
                size=stat.st_size,
                mtime=stat.st_mtime,
                content=_read_text_sample(file_path, max_content_bytes),
            )

            conn.execute(
                """
                INSERT INTO files_metadata(path, name, extension, size, mtime)
                VALUES(:path, :name, :extension, :size, :mtime)
                ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name,
                    extension=excluded.extension,
                    size=excluded.size,
                    mtime=excluded.mtime
                """,
                {
                    "path": record.path,
                    "name": record.name,
                    "extension": record.extension,
                    "size": record.size,
                    "mtime": record.mtime,
                },
            )

            conn.execute(
                """
                INSERT INTO files_content(path, content)
                VALUES(:path, :content)
                ON CONFLICT(path) DO UPDATE SET content=excluded.content
                """,
                {
                    "path": record.path,
                    "content": record.content or "",
                },
            )
            count += 1

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

    conn = sqlite3.connect(str(db_path))
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
