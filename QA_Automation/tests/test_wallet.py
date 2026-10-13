def test_create_wallet(wallet_client):
    user_id = "user-wallet-test"

    wallet = wallet_client.create_wallet(user_id)

    assert wallet["userId"] == user_id
    assert wallet["currency"] == "IDR"
    assert wallet["balance"] == 0


def test_get_wallet(wallet_client):
    user_id = "user-get-wallet"

    wallet = wallet_client.create_wallet(user_id)

    wallet_id = wallet["walletId"]

    result = wallet_client.get_wallet(wallet_id)

    assert result["walletId"] == wallet_id
    assert result["userId"] == user_id
    assert result["currency"] == "IDR"


def test_credit_wallet(wallet_client):
    user_id = "user-credit-test"

    wallet = wallet_client.create_wallet(user_id)
    wallet_id = wallet["walletId"]

    response = wallet_client.credit(
        wallet_id=wallet_id,
        amount=50000,
        idempotency_key="credit-wallet-test-001"
    )

    assert response.status_code == 200

    updated_wallet = wallet_client.get_wallet(wallet_id)

    assert updated_wallet["balance"] == 50000


def test_credit_wallet_creates_transaction(wallet_client):
    user_id = "user-transaction-test"

    wallet = wallet_client.create_wallet(user_id)
    wallet_id = wallet["walletId"]

    response = wallet_client.credit(
        wallet_id=wallet_id,
        amount=50000,
        idempotency_key="credit-transaction-test-001"
    )

    assert response.status_code == 200

    transactions = wallet_client.get_transactions(wallet_id)

    assert len(transactions["transactions"]) == 1

    transaction = transactions["transactions"][0]

    assert transaction["type"] == "CREDIT"
    assert transaction["amount"] == 50000
    assert transaction["balanceAfter"] == 50000

def test_get_non_existing_wallet_returns_error(wallet_client):
    response = wallet_client.client.get(
        f"{wallet_client.base_url}/wallets/non-existing-wallet"
    )

    assert response.status_code == 404

def test_claim_reward_with_invalid_wallet_returns_error(rewards_client):
    response = rewards_client.claim_reward(
        reward_id="rw-coffee",
        user_id="user-test",
        wallet_id="invalid-wallet",
        idempotency_key="invalid-wallet-claim-001"
    )

    assert response.status_code >= 400    