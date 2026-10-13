import httpx


class WalletClient:
    def __init__(self, base_url="http://127.0.0.1:8081"):
        self.base_url = base_url
        self.client = httpx.Client()

    def create_wallet(self, user_id):
        response = self.client.post(
            f"{self.base_url}/wallets",
            json={
                "userId": user_id,
                "currency": "IDR"
            }
        )

        assert response.status_code == 201
        return response.json()

    def get_wallet(self, wallet_id):
        response = self.client.get(
            f"{self.base_url}/wallets/{wallet_id}"
        )

        assert response.status_code == 200
        return response.json()

    def credit(self, wallet_id, amount, idempotency_key):
        response = self.client.post(
            f"{self.base_url}/wallets/{wallet_id}/credit",
            json={
                "amount": amount
            },
            headers={
                "Idempotency-Key": idempotency_key
            }
        )

        return response

    def get_transactions(self, wallet_id):
        response = self.client.get(
            f"{self.base_url}/wallets/{wallet_id}/transactions"
        )

        assert response.status_code == 200
        return response.json()

    def reset(self):
        response = self.client.post(
            f"{self.base_url}/admin/reset"
        )
    
        print("WALLET RESET STATUS:", response.status_code)
        print("WALLET RESET BODY:", response.text)

        return response