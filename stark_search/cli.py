"""Command line interface for the file indexing utilities."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import sys
from typing import Sequence

from .indexer import (
    add_addresses,
    fetch_addresses,
    fetch_recent_events,
    index_directory,
    search_database,
)


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

    events_cmd = sub.add_parser(
        "events",
        help="Show recent indexing events recorded during ingestion.",
    )
    events_cmd.add_argument(
        "--db",
        dest="db_path",
        type=pathlib.Path,
        required=True,
        help="SQLite database created with the 'index' command.",
    )
    events_cmd.add_argument(
        "--limit",
        type=_positive_int,
        default=20,
        help="Maximum number of events to display.",
    )
    events_cmd.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Emit JSON output instead of a formatted table.",
    )

    addresses_cmd = sub.add_parser(
        "addresses",
        help="Manage tracked blockchain or account addresses.",
    )
    addresses_cmd.add_argument(
        "--db",
        dest="db_path",
        type=pathlib.Path,
        required=True,
        help="SQLite database created with the 'index' command.",
    )
    addresses_sub = addresses_cmd.add_subparsers(dest="action", required=True)

    addresses_add = addresses_sub.add_parser(
        "add",
        help="Insert or update an address entry.",
    )
    addresses_add.add_argument(
        "addresses",
        nargs="+",
        help="Address identifier(s) to store.",
    )
    addresses_add.add_argument(
        "--label",
        required=True,
        help="Label describing the owner or purpose of the address.",
    )

    addresses_list = addresses_sub.add_parser(
        "list",
        help="List known addresses.",
    )
    addresses_list.add_argument(
        "--label",
        help="Optional label filter to narrow results.",
    )
    addresses_list.add_argument(
        "--limit",
        type=_positive_int,
        help="Optional maximum number of addresses to display.",
    )
    addresses_list.add_argument(
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


def _print_events(events: Sequence[dict]) -> None:
    if not events:
        print("No events recorded.")
        return

    path_width = max(len(event.get("path") or "") for event in events)
    header = f"Timestamp            Type              {'Path'.ljust(path_width)}  Details"
    print(header)
    print("-" * len(header))

    for event in events:
        timestamp = _format_timestamp(event["timestamp"])
        event_type = event["type"].ljust(18)
        path = (event.get("path") or "").ljust(path_width)
        details = event.get("details") or ""
        print(f"{timestamp}  {event_type}  {path}  {details}")


def _print_addresses(addresses: Sequence[dict]) -> None:
    if not addresses:
        print("No addresses recorded.")
        return

    address_width = max(len(item["address"]) for item in addresses)
    label_width = max(len(item["label"]) for item in addresses)
    header = (
        f"{'Address'.ljust(address_width)}  {'Label'.ljust(label_width)}  Added"
    )
    print(header)
    print("-" * len(header))

    for item in addresses:
        added = _format_timestamp(item["added_at"])
        print(
            f"{item['address'].ljust(address_width)}  "
            f"{item['label'].ljust(label_width)}  {added}"
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

    if args.command == "events":
        events = fetch_recent_events(db_path=args.db_path, limit=args.limit)
        if args.as_json:
            json.dump(events, sys.stdout, indent=2)
            print()
        else:
            _print_events(events)
        return 0

    if args.command == "addresses":
        if args.action == "add":
            records = add_addresses(
                db_path=args.db_path,
                addresses=args.addresses,
                label=args.label,
            )
            for record in records:
                print(
                    "Recorded address",
                    record.address,
                    "with label",
                    record.label,
                )
            return 0

        if args.action == "list":
            addresses = fetch_addresses(
                db_path=args.db_path,
                label=args.label,
                limit=args.limit,
            )
            if args.as_json:
                json.dump(addresses, sys.stdout, indent=2)
                print()
            else:
                _print_addresses(addresses)
            return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
