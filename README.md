# Starkinternational Search Utilities

This project provides a lightweight command line tool for building a
searchable SQLite database of your local files. The indexer walks a target
folder, records file metadata, and stores a text sample for full-text search.
You can then query the database to quickly locate files and snippets that
match your keywords.

## Usage

### Create an index

```
python -m stark_search index /path/to/scan --db ~/file-index.db \
    --ignore "*/.git/*" --ignore "*.pyc"
```

### Search the index

```
python -m stark_search search --db ~/file-index.db "security"
```

Use `--json` to emit machine-readable results.

### Manage and validate addresses

Store address strings in the same SQLite database and optionally validate them
against a live HTTP endpoint:

```
python -m stark_search address --db ~/file-index.db add "123 Example Ave, Gotham"
python -m stark_search address --db ~/file-index.db list
python -m stark_search address --db ~/file-index.db check --all \
    --endpoint https://example.com/address-lookup
```

The `check` sub-command performs a GET request against the provided endpoint
with the address appended as a query parameter. The response is expected to be a
JSON object that includes an `"exists"` flag indicating whether the address is
found in the live database; any additional fields are printed for inspection.

Use `--query-param` to change the address parameter name, `--query key=value`
to add extra query parameters, and `--header "Name: value"` to send additional
HTTP headers.
