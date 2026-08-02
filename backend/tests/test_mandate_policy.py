from __future__ import annotations

from fastapi.testclient import TestClient
from solders.keypair import Keypair


def _create_signed_mandate(
    client: TestClient,
    *,
    policy: dict[str, object],
) -> Keypair:
    investor = Keypair()
    prepared = client.post(
        "/api/v1/investor/mandates/prepare",
        json={"ownerWalletAddress": str(investor.pubkey()), "policy": policy},
    )
    assert prepared.status_code == 200
    signature = str(investor.sign_message(prepared.json()["canonicalMessage"].encode()))
    created = client.post(
        "/api/v1/investor/mandates",
        json={
            "ownerWalletAddress": str(investor.pubkey()),
            "policy": policy,
            "signature": signature,
        },
    )
    assert created.status_code == 200
    return investor


def test_rejects_invalid_wallet_signature(client: TestClient) -> None:
    policy = {
        "totalInvestmentLimitUsdc": 20_000,
        "perInvoiceLimitUsdc": 20_000,
        "buyerAllowlist": ["Prime Mobility"],
        "minimumRiskScore": 80,
        "maximumRemainingTermDays": 100,
        "expiresAt": "2030-12-31",
    }
    owner = Keypair()
    someone_else = Keypair()
    prepared = client.post(
        "/api/v1/investor/mandates/prepare",
        json={"ownerWalletAddress": str(owner.pubkey()), "policy": policy},
    )
    assert prepared.status_code == 200
    response = client.post(
        "/api/v1/investor/mandates",
        json={
            "ownerWalletAddress": str(owner.pubkey()),
            "policy": policy,
            "signature": str(
                someone_else.sign_message(prepared.json()["canonicalMessage"].encode())
            ),
        },
    )
    assert response.status_code == 409
    assert response.json()["message"] == "Mandate 서명을 검증하지 못했습니다."


def test_deposit_receipt_is_idempotent(client: TestClient) -> None:
    policy = {
        "totalInvestmentLimitUsdc": 20_000,
        "perInvoiceLimitUsdc": 20_000,
        "buyerAllowlist": ["Prime Mobility"],
        "minimumRiskScore": 80,
        "maximumRemainingTermDays": 100,
        "expiresAt": "2030-12-31",
    }
    investor = _create_signed_mandate(client, policy=policy)
    payload = {
        "ownerWalletAddress": str(investor.pubkey()),
        "amountUsdc": 1_000,
        "signature": "mock-deposit-signature-idempotent",
    }
    first = client.post("/api/v1/investor/vault/deposits/confirm", json=payload)
    second = client.post("/api/v1/investor/vault/deposits/confirm", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["availableUsdc"] == second.json()["availableUsdc"] == 1_000


def test_agent_keeps_rwa_issued_when_mandate_rejects_buyer(
    client: TestClient,
    contract_files: dict[str, tuple[str, bytes, str]],
) -> None:
    policy = {
        "totalInvestmentLimitUsdc": 50_000,
        "perInvoiceLimitUsdc": 20_000,
        "buyerAllowlist": ["Another Buyer"],
        "minimumRiskScore": 80,
        "maximumRemainingTermDays": 100,
        "expiresAt": "2030-12-31",
    }
    investor = _create_signed_mandate(client, policy=policy)
    deposited = client.post(
        "/api/v1/investor/vault/deposits/confirm",
        json={
            "ownerWalletAddress": str(investor.pubkey()),
            "amountUsdc": 20_000,
            "signature": "mock-deposit-signature-rejected-policy",
        },
    )
    assert deposited.status_code == 200

    created = client.post("/api/v1/invoices", files=contract_files)
    invoice_id = created.json()["invoice"]["id"]
    verification = client.post(
        f"/api/v1/invoices/{invoice_id}/verification-request"
    ).json()["invoice"]["verificationId"]
    confirmed = client.post(f"/api/v1/verifications/{verification}/confirm")
    assert confirmed.status_code == 200

    response = client.post(
        f"/api/v1/invoices/{invoice_id}/offer-response",
        json={"response": "ACCEPT"},
    )
    assert response.status_code == 200
    issued = client.get(f"/api/v1/invoices/{invoice_id}").json()["invoice"]
    assert issued["status"] == "RWA_ISSUED"
    assert issued["agentDecision"]["status"] == "REJECTED"
    assert issued["agentDecision"]["checks"]["buyerAllowlist"] is False
    assert issued["fundingTransaction"] is None
