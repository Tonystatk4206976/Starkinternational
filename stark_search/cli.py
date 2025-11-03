"""Command line interface for the file indexing utilities."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import sys
from typing import Sequence

from .indexer import index_directory, search_database


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Index and search local files using SQLite FTS5.",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    index_cmd = sub.add_parser(
        "index",
        help="Crawl a directory and store metadata in the database.",
    )
    index_cmd.add_argument(
        "root",
        type=pathlib.Path,
        help="Root directory to index.",
    )
    index_cmd.add_argument(
        "--db",
        dest="db_path",
        type=pathlib.Path,
        required=True,
        help="Destination SQLite database file.",
    )
    index_cmd.add_argument(
        "--follow-symlinks",
        action="store_true",
        help="Follow symbolic links while walking the tree.",
    )
    index_cmd.add_argument(
        "--ignore",
        dest="ignore_patterns",
        action="append",
        default=[],
        help="Glob pattern(s) to ignore. Can be supplied multiple times.",
    )
    index_cmd.add_argument(
        "--max-bytes",
        type=_positive_int,
        default=1_000_000,
        help="Maximum number of bytes to read from a file for content indexing.",
    )

    search_cmd = sub.add_parser(
        "search",
        help="Run a full-text search query against the database.",
    )
    search_cmd.add_argument(
        "--db",
        dest="db_path",
        type=pathlib.Path,
        required=True,
        help="SQLite database created with the 'index' command.",
    )
    search_cmd.add_argument(
        "query",
        help="FTS query. Surround terms with quotes to search for phrases.",
    )
    search_cmd.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="Maximum number of results to display.",
    )
    search_cmd.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit JSON output instead of a formatted table.",
    )

    return parser


def _format_timestamp(timestamp: float) -> str:
    dt = _dt.datetime.fromtimestamp(timestamp)
    return dt.isoformat(sep=" ", timespec="seconds")


def _print_table(results: Sequence[dict]) -> None:
    if not results:
        print("No results found.")
        return

    path_width = max(len(result["path"]) for result in results)
    header = f"{'Path'.ljust(path_width)}  Size    Modified             Snippet"
    print(header)
    print("-" * len(header))

    for row in results:
        snippet = row.get("snippet") or ""
        snippet = snippet.replace("\n", " ")
        print(
            f"{row['path'].ljust(path_width)}  {row['size']:>8}  "
            f"{_format_timestamp(row['mtime'])}  {snippet}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "index":
        count = index_directory(
            root=args.root,
            db_path=args.db_path,
            follow_symlinks=args.follow_symlinks,
            ignore_patterns=args.ignore_patterns,
            max_content_bytes=args.max_bytes,
        )
        print(f"Indexed {count} files into {args.db_path}")
        return 0

    if args.command == "search":
        results = search_database(
            db_path=args.db_path,
            query=args.query,
            limit=args.limit,
        )
        if args.as_json:
            json.dump(results, sys.stdout, indent=2)
            print()
        else:
            _print_table(results)
        return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
