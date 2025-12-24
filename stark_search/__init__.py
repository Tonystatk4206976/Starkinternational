"""Utilities for indexing files and validating stored addresses."""

from .address_book import add_address, check_address_live, list_addresses
from .indexer import index_directory, initialize_database, search_database

__all__ = [
    "add_address",
    "check_address_live",
    "index_directory",
    "initialize_database",
    "list_addresses",
    "search_database",
]
