from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import WalletCategory

# Configure an in-memory database for testing
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SQLModel.metadata.create_all(engine)


def get_session_override():
    with Session(engine) as session:
        yield session


def setup_module() -> None:
    app.dependency_overrides[get_session] = get_session_override


def teardown_module() -> None:
    app.dependency_overrides.clear()


def test_wallet_lifecycle():
    client = TestClient(app)
    wallet_payload = {
        "address": "0xdormitprime00000000000000000000000003",
        "label": "Dormit Yield Vault",
        "category": WalletCategory.defi.value,
        "provider": "Dormit",
        "network": "Polygon",
        "verified": True,
        "tags": ["yield", "defi"],
        "notes": "Dormit vault used for staking rewards",
    }

    response = client.post("/wallets", json=wallet_payload)
    assert response.status_code == 201, response.text
    wallet = response.json()
    wallet_id = wallet["id"]

    # Refresh using static data connector
    refresh_response = client.post(f"/wallets/{wallet_id}/refresh")
    assert refresh_response.status_code == 200, refresh_response.text
    snapshot = refresh_response.json()
    assert snapshot["total_usd"] == 7700.0
    assert snapshot["native_symbol"] == "MATIC"

    # Summary report should include Dormit totals
    summary = client.get("/reports/summary").json()
    assert summary["overall_usd"] == 7700.0
    assert summary["by_provider"]["Dormit"] == 7700.0
    assert summary["by_category"][WalletCategory.defi.value] == 7700.0

    # List wallets should show latest snapshot metadata
    wallets_response = client.get("/wallets")
    assert wallets_response.status_code == 200
    wallets = wallets_response.json()
    assert len(wallets) == 1
    assert wallets[0]["latest_snapshot"]["total_usd"] == 7700.0
