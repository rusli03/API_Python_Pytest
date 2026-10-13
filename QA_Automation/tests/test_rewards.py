def test_get_non_existing_reward_returns_error(rewards_client):
    response = rewards_client.client.get(
        f"{rewards_client.base_url}/rewards/invalid-reward"
    )

    assert response.status_code == 404