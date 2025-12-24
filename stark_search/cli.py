"""Command line interface for the file indexing utilities."""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import pathlib
import sys
from typing import Sequence

from .address_book import add_address, check_address_live, list_addresses
from .indexer import index_directory, search_database


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc

    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _parse_key_value(value: str, *, separator: str, label: str) -> tuple[str, str]:
    if separator not in value:
        raise argparse.ArgumentTypeError(
            f"{label} must include '{separator}' (got {value!r})"
        )
    key, raw_value = value.split(separator, 1)
    key = key.strip()
    raw_value = raw_value.strip()
    if not key:
        raise argparse.ArgumentTypeError(f"{label} key must not be empty")
    if not raw_value:
        raise argparse.ArgumentTypeError(f"{label} value must not be empty")
    return key, raw_value


def _parse_query(value: str) -> tuple[str, str]:
    return _parse_key_value(value, separator="=", label="query parameter")


def _parse_header(value: str) -> tuple[str, str]:
    return _parse_key_value(value, separator=":", label="header")


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

    address_cmd = sub.add_parser(
        "address",
        help="Manage address records and validate them against a live database.",
    )
    address_cmd.add_argument(
        "--db",
        dest="db_path",
        type=pathlib.Path,
        required=True,
        help="SQLite database file used to store addresses.",
    )

    address_sub = address_cmd.add_subparsers(dest="address_command", required=True)

    address_add = address_sub.add_parser(
        "add",
        help="Store an address in the local database.",
    )
    address_add.add_argument("address", help="The address text to store.")

    address_list = address_sub.add_parser(
        "list",
        help="List stored addresses.",
    )

    address_check = address_sub.add_parser(
        "check",
        help="Validate one or more addresses using a live HTTP endpoint.",
    )
    address_check.add_argument(
        "--endpoint",
        required=True,
        help="Fully-qualified URL to query. The address is appended as a query parameter.",
    )
    address_check.add_argument(
        "--query-param",
        default="address",
        help="Query parameter name used to send the address.",
    )
    address_check.add_argument(
        "--query",
        action="append",
        type=_parse_query,
        default=[],
        help="Extra query parameters to include (key=value).",
    )
    address_check.add_argument(
        "--header",
        action="append",
        type=_parse_header,
        default=[],
        help="Additional HTTP headers to send (Header: value).",
    )
    address_check.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout, in seconds, for the HTTP request.",
    )
    group = address_check.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--address",
        help="Validate a single address without storing it first.",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Validate every address stored in the database.",
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

    if args.command == "address":
        if args.address_command == "add":
            inserted = add_address(args.db_path, args.address)
            if inserted:
                print(f"Stored address in {args.db_path}: {args.address}")
            else:
                print("Address already present in database.")
            return 0

        if args.address_command == "list":
            rows = list_addresses(args.db_path)
            if not rows:
                print("No addresses stored.")
                return 0
            width = max(len(row["address"]) for row in rows)
            print(f"{'Address'.ljust(width)}  Created")
            print("-" * (width + 10))
            for row in rows:
                print(f"{row['address'].ljust(width)}  {row['created_at']}")
            return 0

        if args.address_command == "check":
            if args.address:
                targets = [args.address]
            else:
                targets = [row["address"] for row in list_addresses(args.db_path)]
                if not targets:
                    print("No addresses stored to validate.")
                    return 0

            extra_query = dict(args.query)
            headers = dict(args.header)
            for target in targets:
                try:
                    payload = check_address_live(
                        target,
                        endpoint=args.endpoint,
                        timeout=args.timeout,
                        extra_query=extra_query,
                        query_param=args.query_param,
                        headers=headers,
                    )
                except Exception as exc:  # pragma: no cover - network dependent
                    print(f"{target}: ERROR - {exc}")
                    continue

                exists = payload.get("exists")
                status = "MATCH" if exists else "NOT FOUND"
                print(f"{target}: {status}")
                extra = {
                    key: value
                    for key, value in payload.items()
                    if key not in {"exists", "query_address"}
                }
                if extra:
                    print(json.dumps(extra, indent=2))
            return 0

    parser.error("Unknown command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
