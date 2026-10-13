def test_user_can_claim_reward_and_wallet_is_debited(
    wallet_client,
    rewards_client,
    funded_wallet
):
    reward_id = "rw-coffee"

    before_wallet = wallet_client.get_wallet(
        funded_wallet["wallet_id"]
    )

    reward = rewards_client.get_reward(reward_id)

    response = rewards_client.claim_reward(
        reward_id=reward_id,
        user_id=funded_wallet["user_id"],
        wallet_id=funded_wallet["wallet_id"],
        idempotency_key="claim-success-001"
    )

    assert response.status_code == 201

    claim = response.json()

    assert claim["status"] == "FULFILLED"
    assert claim["debitedAmount"] == reward["cost"]
    assert claim["walletTransactionId"] is not None

    after_wallet = wallet_client.get_wallet(
        funded_wallet["wallet_id"]
    )

    assert after_wallet["balance"] == (
        before_wallet["balance"] - reward["cost"]
    )

    transactions = wallet_client.get_transactions(
        funded_wallet["wallet_id"]
    )

    assert len(transactions["transactions"]) == 2

    debit = transactions["transactions"][-1]

    assert debit["type"] == "DEBIT"
    assert debit["amount"] == reward["cost"]
    assert debit["balanceAfter"] == after_wallet["balance"]