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
