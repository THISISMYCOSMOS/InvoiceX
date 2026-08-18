"""Privy user lookup and user-owned Solana wallet provisioning."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol, cast
from urllib.parse import quote

import httpx
from fastapi import status

from invoicex_backend.config import BackendSettings
from invoicex_backend.errors import OnboardingApiError


@dataclass(frozen=True, slots=True)
class PrivyWalletRecord:
    id: str
    address: str
    user_id: str


class PrivyUserGateway(Protocol):
    async def verified_email(self, user_id: str) -> str: ...

    async def get_or_create_solana_wallet(
        self,
        user_id: str,
        *,
        idempotency_key: str,
    ) -> PrivyWalletRecord: ...

    async def aclose(self) -> None: ...


class HttpPrivyUserGateway:
    def __init__(
        self,
        settings: BackendSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            timeout=settings.privy_api_timeout_seconds
        )

    def _configuration(self) -> tuple[str, str]:
        app_id = (self._settings.privy_app_id or "").strip()
        app_secret = (self._settings.privy_app_secret or "").strip()
        if not app_id or not app_secret:
            raise OnboardingApiError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "PRIVY_CONFIGURATION_MISSING",
                "Privy 사용자·지갑 설정이 완료되지 않았습니다.",
            )
        return app_id, app_secret

    def _request_options(self) -> tuple[dict[str, str], httpx.BasicAuth]:
        app_id, app_secret = self._configuration()
        return {"privy-app-id": app_id}, httpx.BasicAuth(app_id, app_secret)

    async def verified_email(self, user_id: str) -> str:
        headers, auth = self._request_options()
        try:
            response = await self._client.get(
                f"{self._settings.privy_api_base_url}/v1/users/{quote(user_id, safe='')}",
                headers=headers,
                auth=auth,
            )
            response.raise_for_status()
            payload = cast(dict[str, object], response.json())
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "PRIVY_USER_LOOKUP_FAILED",
                "Privy 사용자 정보를 확인하지 못했습니다.",
            ) from exc
        accounts = payload.get("linked_accounts")
        if isinstance(accounts, list):
            for account in accounts:
                if not isinstance(account, dict) or account.get("type") != "email":
                    continue
                address = account.get("address")
                if isinstance(address, str) and address.strip():
                    return address.strip().lower()
        raise OnboardingApiError(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "PRIVY_VERIFIED_EMAIL_MISSING",
            "Privy 계정에 인증된 이메일이 없습니다.",
        )

    async def get_or_create_solana_wallet(
        self,
        user_id: str,
        *,
        idempotency_key: str,
    ) -> PrivyWalletRecord:
        existing = await self._find_solana_wallet(user_id)
        if existing is not None:
            return existing

        headers, auth = self._request_options()
        headers = {
            **headers,
            "privy-idempotency-key": idempotency_key,
            "Content-Type": "application/json",
        }
        external_id = f"invoicex_{hashlib.sha256(user_id.encode()).hexdigest()[:48]}"
        try:
            response = await self._client.post(
                f"{self._settings.privy_api_base_url}/v1/wallets",
                headers=headers,
                auth=auth,
                json={
                    "chain_type": "solana",
                    "external_id": external_id,
                    "owner": {"user_id": user_id},
                },
            )
            response.raise_for_status()
            return self._wallet_from_payload(response.json(), user_id)
        except OnboardingApiError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "사용자 소유 Solana Embedded Wallet을 생성하지 못했습니다.",
            ) from exc

    async def _find_solana_wallet(self, user_id: str) -> PrivyWalletRecord | None:
        headers, auth = self._request_options()
        try:
            response = await self._client.get(
                f"{self._settings.privy_api_base_url}/v1/wallets",
                headers=headers,
                auth=auth,
                params={"user_id": user_id, "chain_type": "solana", "limit": 100},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "기존 Solana Embedded Wallet을 확인하지 못했습니다.",
            ) from exc
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "Privy Wallet 응답 형식이 올바르지 않습니다.",
            )
        candidates: list[tuple[int, PrivyWalletRecord]] = []
        for row in rows:
            if not isinstance(row, dict) or row.get("chain_type") != "solana":
                continue
            try:
                wallet = self._wallet_from_payload(row, user_id)
            except OnboardingApiError:
                continue
            created_at = row.get("created_at")
            candidates.append((int(created_at) if isinstance(created_at, int) else 0, wallet))
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]

    @staticmethod
    def _wallet_from_payload(payload: object, expected_user_id: str) -> PrivyWalletRecord:
        if not isinstance(payload, dict):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "Privy Wallet 응답 형식이 올바르지 않습니다.",
            )
        wallet_id = payload.get("id")
        address = payload.get("address")
        if (
            payload.get("chain_type") != "solana"
            or not isinstance(wallet_id, str)
            or not isinstance(address, str)
        ):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_RESPONSE_INVALID",
                "Privy Wallet 응답 형식이 올바르지 않습니다.",
            )
        return PrivyWalletRecord(id=wallet_id, address=address, user_id=expected_user_id)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
