import pytest

from clients.wallet_client import WalletClient
from clients.rewards_client import RewardsClient


@pytest.fixture
def wallet_client():
    return WalletClient()


@pytest.fixture
def rewards_client():
    return RewardsClient()


@pytest.fixture(autouse=True)
def reset_services(wallet_client, rewards_client):
    wallet_client.reset()
    rewards_client.reset()

    yield


@pytest.fixture
def funded_wallet(wallet_client):
    user_id = "user-test"

    wallet = wallet_client.create_wallet(user_id)

    wallet_client.credit(
        wallet_id=wallet["walletId"],
        amount=100000,
        idempotency_key=f"credit-{wallet['walletId']}"
    )

    return {
        "user_id": user_id,
        "wallet_id": wallet["walletId"]
    }