import httpx


class RewardsClient:
    def __init__(self, base_url="http://127.0.0.1:8082"):
        self.base_url = base_url
        self.client = httpx.Client()

    def get_reward(self, reward_id):
        response = self.client.get(
            f"{self.base_url}/rewards/{reward_id}"
        )

        assert response.status_code == 200
        return response.json()

    def claim_reward(
        self,
        reward_id,
        user_id,
        wallet_id,
        idempotency_key
    ):
        return self.client.post(
            f"{self.base_url}/rewards/{reward_id}/claims",
            json={
                "userId": user_id,
                "walletId": wallet_id
            },
            headers={
                "Idempotency-Key": idempotency_key
            }
        )

    def get_claim(self, claim_id):
        response = self.client.get(
            f"{self.base_url}/claims/{claim_id}"
        )

        assert response.status_code == 200
        return response.json()

    def reset(self):
        response = self.client.post(
            f"{self.base_url}/admin/reset"
        )

        print("REWARDS RESET STATUS:", response.status_code)
        print("REWARDS RESET BODY:", response.text)

        return response
        