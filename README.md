# Starkinternational Wallet Aggregator

This project provides an API for aggregating and monitoring exchange-verified and DeFi wallets from providers such as **WalaWallet**, **Dormit**, and **Wicket**. It combines balances from both custodial and self-custodied accounts into a single dashboard API similar to tools like CryptoSleuth or WalletWatchTracker.

## Features

- Register wallets with metadata including provider, verification status, category, and descriptive tags.
- Refresh balances using configurable connectors (static data by default, with an Ethplorer connector available for Ethereum wallets).
- Store historical balance snapshots to understand valuation changes over time.
- Summarise holdings across providers and wallet categories for treasury reporting.
- Seed script to load curated wallets for the last two years focusing on WalaWallet, Dormit, and Wicket strategies.

## Project Structure

```
app/
  core/          # Configuration helpers
  services/      # Balance connectors and refresh orchestration
  models.py      # SQLModel ORM models and schemas
  crud.py        # Database CRUD helpers
  main.py        # FastAPI application entrypoint
scripts/
  seed_data.py   # Populate the database with sample wallets and snapshots
data/
  static_balances.json  # Offline balance data used by the static connector
tests/
  test_wallets.py       # API regression tests
requirements.txt
```

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the API**

   ```bash
   uvicorn app.main:app --reload
   ```

   The service exposes endpoints such as `POST /wallets`, `POST /wallets/{id}/refresh`, and `GET /reports/summary`.

3. **Seed example data** (optional)

   ```bash
   python scripts/seed_data.py
   ```

   The seed script creates representative wallets for WalaWallet, Dormit, and Wicket using the curated static balances for the past two years.

4. **Run tests**

   ```bash
   pytest
   ```

## Configuration

Environment variables prefixed with `WALLET_TRACKER_` control runtime behaviour:

- `WALLET_TRACKER_DATABASE_URL`: Database connection string (defaults to `sqlite:///./wallet_tracker.db`).
- `WALLET_TRACKER_STATIC_BALANCE_FILE`: Path to the static balance JSON file.
- `WALLET_TRACKER_ETHPLORER_API_KEY`: API key for the Ethplorer connector.
- `WALLET_TRACKER_PROVIDER_CONNECTOR_MAP`: JSON mapping of providers to connector identifiers (e.g. `{ "WalaWallet": "ethplorer" }`).

## API Highlights

- `POST /wallets` — Register a new wallet with category, provider, and verification status.
- `POST /wallets/{wallet_id}/refresh` — Refresh balances for a wallet using the configured connector and store a snapshot.
- `GET /wallets` — List wallets with optional filters by provider, category, verification status, or tag.
- `GET /wallets/{wallet_id}/snapshots` — Inspect the historical balance snapshots for a wallet.
- `GET /reports/summary` — Aggregated USD valuation grouped by provider and category with an overall total.

## Extending Connectors

Connectors live under `app/services/connectors`. The default static connector reads curated JSON data, while the Ethplorer connector demonstrates how to integrate live blockchain data. To add a new provider:

1. Implement a class that subclasses `BalanceConnector` and returns a `BalanceReport`.
2. Register it in `app/services/registry.py`.
3. Update `WALLET_TRACKER_PROVIDER_CONNECTOR_MAP` to point the provider name to the connector key.

## License

MIT
