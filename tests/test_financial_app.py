from decimal import Decimal

import pytest

from financial_app import (
    AssetHolding,
    AssetManager,
    CloudDocumentImporter,
    CloudSource,
    WalletReference,
    build_profile,
    profile_fingerprint,
)


def test_cloud_importer_normalizes_csv_and_json_transactions(tmp_path):
    drive = tmp_path / "drive"
    drive.mkdir()
    (drive / "checking.csv").write_text(
        "date,description,amount,currency,account,category\n"
        "2026-01-02,Coffee,-4.50,usd,Checking,Food\n",
        encoding="utf-8",
    )
    (drive / "brokerage.json").write_text(
        '[{"posted_at":"01/03/2026","description":"Dividend","amount":"12.34",'
        '"currency":"USD","account":"Brokerage","category":"Income"}]',
        encoding="utf-8",
    )

    importer = CloudDocumentImporter([CloudSource("google_drive", drive)])

    transactions = importer.import_transactions()

    assert [transaction.description for transaction in transactions] == ["Dividend", "Coffee"]
    assert transactions[0].amount == Decimal("12.34")
    assert transactions[1].currency == "USD"
    assert transactions[1].source_provider == "google_drive"


def test_profile_summarizes_cashflow_and_spending(tmp_path):
    dropbox = tmp_path / "dropbox"
    dropbox.mkdir()
    (dropbox / "card.csv").write_text(
        "date,description,amount,category\n"
        "2026-02-01,Paycheck,2500.00,Income\n"
        "2026-02-02,Rent,-1400.00,Housing\n",
        encoding="utf-8",
    )

    profile = build_profile(
        [CloudSource("dropbox", dropbox)],
        [WalletReference("Main ETH", "ethereum", "0x52908400098527886E0F7030069857D2E4169EE7")],
    )

    assert profile.net_cashflow() == Decimal("1100.00")
    assert profile.spending_by_category() == {"Housing": Decimal("1400.00")}
    assert len(profile_fingerprint(profile)) == 64


def test_profile_shows_owned_assets_and_managers(tmp_path):
    onedrive = tmp_path / "onedrive"
    onedrive.mkdir()
    (onedrive / "portfolio.assets.csv").write_text(
        "asset,asset_type,quantity,value,currency,account,manager,manager_type\n"
        "VTI,etf,12.5,3125.00,USD,Roth IRA,Vanguard,custodian\n"
        "Emergency Fund,cash,1,10000.00,USD,Savings,Local Credit Union,bank\n",
        encoding="utf-8",
    )

    profile = build_profile(
        [CloudSource("onedrive", onedrive)],
        [
            WalletReference(
                "Cold Wallet",
                "bitcoin",
                "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kygt080",
                manager=AssetManager("Self Custody", "self"),
            )
        ],
        assets=[
            AssetHolding(
                "Private Note",
                "debt",
                Decimal("1"),
                Decimal("500.00"),
                manager=AssetManager("Family Office", "advisor"),
            )
        ],
    )

    rows = profile.unified_asset_view()

    assert profile.total_assets() == Decimal("13625.00")
    assert profile.assets_by_manager() == {
        "Family Office": Decimal("500.00"),
        "Local Credit Union": Decimal("10000.00"),
        "Vanguard": Decimal("3125.00"),
    }
    assert [(row.asset_name, row.manager_name) for row in rows] == [
        ("Private Note", "Family Office"),
        ("Emergency Fund", "Local Credit Union"),
        ("Bitcoin wallet: Cold Wallet", "Self Custody"),
        ("VTI", "Vanguard"),
    ]


def test_asset_importer_keeps_asset_files_out_of_transactions(tmp_path):
    drive = tmp_path / "drive"
    drive.mkdir()
    (drive / "holdings.assets.json").write_text(
        '{"assets":[{"name":"AAPL","asset_type":"stock","quantity":"3",'
        '"market_value":"600","manager_name":"Fidelity","manager_type":"brokerage"}]}',
        encoding="utf-8",
    )

    importer = CloudDocumentImporter([CloudSource("google_drive", drive)])

    assert [path.name for path in importer.discover_documents()] == ["holdings.assets.json"]
    assert importer.import_transactions() == []
    assert importer.import_assets()[0].manager.name == "Fidelity"


def test_wallet_reference_rejects_private_keys_and_seed_phrases():
    with pytest.raises(ValueError, match="private keys"):
        WalletReference("Do not save", "ethereum", "0x" + "a" * 64)

    with pytest.raises(ValueError, match="seed phrases"):
        WalletReference(
            "Seed",
            "bitcoin",
            "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu",
        )


def test_cloud_source_rejects_unknown_provider(tmp_path):
    with pytest.raises(ValueError, match="provider must be one of"):
        CloudSource("unknown", tmp_path)
