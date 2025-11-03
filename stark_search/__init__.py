"""Utilities for indexing and searching local files."""

from .indexer import index_directory, initialize_database, search_database

__all__ = [
    "index_directory",
    "initialize_database",
    "search_database",
]
