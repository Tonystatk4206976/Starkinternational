# CLI Reference

The `stark_search` CLI provides two subcommands for indexing files and querying
an existing index.

## Command overview

```
python -m stark_search index <root> --db <path> [options]
python -m stark_search search --db <path> <query> [options]
```

## `index`

Crawl a directory tree and store file metadata plus a text sample in an SQLite
FTS5 database.

```
python -m stark_search index <root> --db <path> [options]
```

| Argument | Required | Description |
| --- | --- | --- |
| `root` | Yes | Root directory to index. |
| `--db` | Yes | Destination SQLite database file. |
| `--follow-symlinks` | No | Follow symbolic links while walking the tree. |
| `--ignore` | No | Glob pattern(s) to ignore. Can be supplied multiple times. |
| `--max-bytes` | No | Maximum number of bytes to read from a file for content indexing (default: 1,000,000). |

### Example

```
python -m stark_search index ~/docs --db ~/file-index.db \
  --ignore "*/.git/*" --ignore "*.log" --max-bytes 500000
```

## `search`

Run a full-text query against an existing database.

```
python -m stark_search search --db <path> <query> [options]
```

| Argument | Required | Description |
| --- | --- | --- |
| `--db` | Yes | SQLite database created with the `index` command. |
| `query` | Yes | FTS query. Surround terms with quotes to search for phrases. |
| `--limit` | No | Maximum number of results to display (default: 20). |
| `--json` | No | Emit JSON output instead of a formatted table. |

### Example

```
python -m stark_search search --db ~/file-index.db "security update" --limit 10
```
