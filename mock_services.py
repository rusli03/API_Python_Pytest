"""
mock_services.py — stateful, in-memory mock of the Wallet and Rewards services

Run:   pip install fastapi uvicorn httpx
       python mock_services.py
Wallet  -> http://127.0.0.1:8081   (docs: /docs)
Rewards -> http://127.0.0.1:8082   (docs: /docs)

Rewards calls Wallet over HTTP to debit the claim cost, so cross-service
behaviour is real, not simulated. POST /admin/reset on either service wipes
that service's state. State is lost on restart.
"""
import threading
import uuid
from typing import Optional

import httpx
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

WALLET_URL = "http://127.0.0.1:8081"
WALLET_LOCK = threading.RLock()
REWARDS_LOCK = threading.RLock()


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
class ApiError(HTTPException):
    def __init__(self, status: int, code: str, message: str, **extra):
        super().__init__(status_code=status, detail={"code": code, "message": message, **extra})


def install_error_envelope(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _handler(_: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content={"error": detail})


def require_key(key: Optional[str]) -> str:
    if not key:
        raise ApiError(400, "IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header is required")
    return key


# --------------------------------------------------------------------------- #
# Wallet service (port 8081)
# --------------------------------------------------------------------------- #
wallet_app = FastAPI(title="Wallet Service", version="1.0.0")
install_error_envelope(wallet_app)

WALLETS: dict = {}          # walletId -> wallet dict (includes private "transactions")
WALLET_IDEM: dict = {}      # (walletId, key) -> (body, response)


class CreateWalletRequest(BaseModel):
    userId: str
    currency: str = "IDR"


class MoneyRequest(BaseModel):
    amount: int
    reference: Optional[str] = None


def _wallet(wallet_id: str) -> dict:
    w = WALLETS.get(wallet_id)
    if not w:
        raise ApiError(404, "WALLET_NOT_FOUND", f"Wallet {wallet_id} does not exist")
    return w


def _public(w: dict) -> dict:
    return {k: v for k, v in w.items() if k != "transactions"}


def _apply(wallet_id: str, kind: str, body: MoneyRequest, key: str) -> dict:
    with WALLET_LOCK:
        w = _wallet(wallet_id)
        idem_key = (wallet_id, key)
        if idem_key in WALLET_IDEM:
            prev_body, prev_resp = WALLET_IDEM[idem_key]
            if prev_body != body.model_dump():
                raise ApiError(422, "IDEMPOTENCY_MISMATCH", "Idempotency-Key reused with a different payload")
            return prev_resp
        if body.amount <= 0:
            raise ApiError(422, "INVALID_AMOUNT", "amount must be a positive integer")
        if kind == "DEBIT" and w["balance"] < body.amount:
            raise ApiError(409, "INSUFFICIENT_FUNDS", "Wallet balance is insufficient",
                           balance=w["balance"], requested=body.amount)
        w["balance"] += body.amount if kind == "CREDIT" else -body.amount
        w["version"] += 1
        txn = {"transactionId": str(uuid.uuid4()), "type": kind, "amount": body.amount,
               "reference": body.reference, "balanceAfter": w["balance"]}
        w["transactions"].append(txn)
        resp = {"walletId": wallet_id, "balance": w["balance"], "version": w["version"], "transaction": txn}
        WALLET_IDEM[idem_key] = (body.model_dump(), resp)
        return resp


@wallet_app.post("/wallets", status_code=201)
def create_wallet(body: CreateWalletRequest):
    with WALLET_LOCK:
        wallet_id = str(uuid.uuid4())
        WALLETS[wallet_id] = {"walletId": wallet_id, "userId": body.userId, "currency": body.currency,
                              "balance": 0, "version": 0, "transactions": []}
        return _public(WALLETS[wallet_id])


@wallet_app.get("/wallets/{wallet_id}")
def get_wallet(wallet_id: str):
    return _public(_wallet(wallet_id))


@wallet_app.post("/wallets/{wallet_id}/credit")
def credit(wallet_id: str, body: MoneyRequest, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
    return _apply(wallet_id, "CREDIT", body, require_key(idempotency_key))


@wallet_app.post("/wallets/{wallet_id}/debit")
def debit(wallet_id: str, body: MoneyRequest, idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
    return _apply(wallet_id, "DEBIT", body, require_key(idempotency_key))


@wallet_app.get("/wallets/{wallet_id}/transactions")
def transactions(wallet_id: str):
    return {"walletId": wallet_id, "transactions": list(_wallet(wallet_id)["transactions"])}


@wallet_app.post("/admin/reset", status_code=204)
def wallet_reset():
    with WALLET_LOCK:
        WALLETS.clear()
        WALLET_IDEM.clear()


# --------------------------------------------------------------------------- #
# Rewards service (port 8082)
# --------------------------------------------------------------------------- #
rewards_app = FastAPI(title="Rewards Service", version="1.0.0")
install_error_envelope(rewards_app)

SEED_REWARDS = [
    {"rewardId": "rw-coffee", "name": "Coffee voucher", "cost": 25000, "stock": 100, "maxClaimsPerUser": None},
    {"rewardId": "rw-headphones", "name": "Wireless headphones", "cost": 750000, "stock": 3, "maxClaimsPerUser": 1},
    {"rewardId": "rw-badge", "name": "Early adopter badge", "cost": 0, "stock": None, "maxClaimsPerUser": 1},
]
REWARDS: dict = {}
CLAIMS: dict = {}          # claimId -> claim
CLAIM_IDEM: dict = {}      # (rewardId, key) -> (body, status, response)


def _seed():
    REWARDS.clear()
    for r in SEED_REWARDS:
        REWARDS[r["rewardId"]] = dict(r)


_seed()


class ClaimRequest(BaseModel):
    userId: str
    walletId: str


def _reward(reward_id: str) -> dict:
    r = REWARDS.get(reward_id)
    if not r:
        raise ApiError(404, "REWARD_NOT_FOUND", f"Reward {reward_id} does not exist")
    return r


def _fulfilled_claims(user_id: str, reward_id: str) -> int:
    return sum(1 for c in CLAIMS.values()
               if c["userId"] == user_id and c["rewardId"] == reward_id and c["status"] == "FULFILLED")


@rewards_app.get("/rewards")
def list_rewards():
    return {"rewards": list(REWARDS.values())}


@rewards_app.get("/rewards/{reward_id}")
def get_reward(reward_id: str):
    return _reward(reward_id)


@rewards_app.post("/rewards/{reward_id}/claims", status_code=201)
def claim_reward(reward_id: str, body: ClaimRequest,
                 idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key")):
    key = require_key(idempotency_key)
    with REWARDS_LOCK:
        reward = _reward(reward_id)
        idem = (reward_id, key)
        if idem in CLAIM_IDEM:
            prev_body, prev_status, prev_resp = CLAIM_IDEM[idem]
            if prev_body != body.model_dump():
                raise ApiError(422, "IDEMPOTENCY_MISMATCH", "Idempotency-Key reused with a different payload")
            return JSONResponse(status_code=prev_status, content=prev_resp)

        if reward["stock"] is not None and reward["stock"] <= 0:
            raise ApiError(409, "REWARD_OUT_OF_STOCK", "Reward has no remaining stock")
        if reward["maxClaimsPerUser"] is not None and _fulfilled_claims(body.userId, reward_id) >= reward["maxClaimsPerUser"]:
            raise ApiError(409, "ALREADY_CLAIMED", "User has reached the claim limit for this reward")

        claim_id = str(uuid.uuid4())
        claim = {"claimId": claim_id, "rewardId": reward_id, "userId": body.userId, "walletId": body.walletId,
                 "status": "PENDING", "debitedAmount": 0, "walletTransactionId": None, "rejectionReason": None}

        if reward["cost"] > 0:
            try:
                resp = httpx.post(f"{WALLET_URL}/wallets/{body.walletId}/debit",
                                  json={"amount": reward["cost"], "reference": f"claim:{claim_id}"},
                                  headers={"Idempotency-Key": f"claim:{claim_id}"}, timeout=5.0)
            except httpx.HTTPError:
                raise ApiError(502, "WALLET_UNAVAILABLE", "Wallet service could not be reached")
            if resp.status_code == 404:
                raise ApiError(422, "WALLET_NOT_FOUND", "walletId does not exist in Wallet service")
            if resp.status_code == 409:
                claim["status"] = "REJECTED"
                claim["rejectionReason"] = "INSUFFICIENT_BALANCE"
                CLAIMS[claim_id] = claim
                err = ApiError(409, "INSUFFICIENT_BALANCE", "Wallet balance is insufficient for this reward",
                               claimId=claim_id, cost=reward["cost"])
                CLAIM_IDEM[idem] = (body.model_dump(), 409, {"error": err.detail})
                raise err
            if resp.status_code != 200:
                raise ApiError(502, "WALLET_ERROR", f"Wallet service returned {resp.status_code}")
            claim["debitedAmount"] = reward["cost"]
            claim["walletTransactionId"] = resp.json()["transaction"]["transactionId"]

        claim["status"] = "FULFILLED"
        if reward["stock"] is not None:
            reward["stock"] -= 1
        CLAIMS[claim_id] = claim
        CLAIM_IDEM[idem] = (body.model_dump(), 201, claim)
        return claim


@rewards_app.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    c = CLAIMS.get(claim_id)
    if not c:
        raise ApiError(404, "CLAIM_NOT_FOUND", f"Claim {claim_id} does not exist")
    return c


@rewards_app.get("/users/{user_id}/claims")
def user_claims(user_id: str):
    return {"userId": user_id, "claims": [c for c in CLAIMS.values() if c["userId"] == user_id]}


@rewards_app.post("/admin/reset", status_code=204)
def rewards_reset():
    with REWARDS_LOCK:
        CLAIMS.clear()
        CLAIM_IDEM.clear()
        _seed()


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    def run(app, port):
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

    threading.Thread(target=run, args=(wallet_app, 8081), daemon=True).start()
    print("Wallet  service: http://127.0.0.1:8081/docs")
    print("Rewards service: http://127.0.0.1:8082/docs")
    run(rewards_app, 8082)
