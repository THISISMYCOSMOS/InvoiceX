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

    async def delete_user(self, user_id: str) -> None: ...

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

    async def delete_user(self, user_id: str) -> None:
        headers, auth = self._request_options()
        try:
            response = await self._client.delete(
                f"{self._settings.privy_api_base_url}/v1/users/{quote(user_id, safe='')}",
                headers=headers,
                auth=auth,
            )
            if response.status_code == status.HTTP_404_NOT_FOUND:
                return
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "PRIVY_USER_DELETION_FAILED",
                "Privy 사용자 정보를 삭제하지 못했습니다.",
            ) from exc

    async def get_or_create_solana_wallet(
        self,
        user_id: str,
        *,
        idempotency_key: str,
    ) -> PrivyWalletRecord:
        external_id = self._wallet_external_id(user_id)
        existing = await self._find_solana_wallet(user_id, external_id)
        if existing is not None:
            return existing

        headers, auth = self._request_options()
        headers = {
            **headers,
            "privy-idempotency-key": idempotency_key,
            "Content-Type": "application/json",
        }
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
            wallet_id = self._wallet_id_from_creation_response(response.json())
            return await self._get_solana_wallet(wallet_id, user_id, external_id)
        except OnboardingApiError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "사용자 소유 Solana Embedded Wallet을 생성하지 못했습니다.",
            ) from exc

    @staticmethod
    def _wallet_external_id(user_id: str) -> str:
        return f"invoicex_{hashlib.sha256(user_id.encode()).hexdigest()[:48]}"

    async def _get_solana_wallet(
        self,
        wallet_id: str,
        user_id: str,
        external_id: str,
    ) -> PrivyWalletRecord:
        headers, auth = self._request_options()
        try:
            response = await self._client.get(
                f"{self._settings.privy_api_base_url}/v1/wallets/{quote(wallet_id, safe='')}",
                headers=headers,
                auth=auth,
            )
            response.raise_for_status()
            payload = response.json()
            wallet = self._wallet_from_payload(
                payload,
                user_id,
                external_id,
                allow_missing_external_id=True,
                allow_missing_owner=True,
            )
        except OnboardingApiError:
            raise
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "생성된 Solana Embedded Wallet의 상세 정보를 확인하지 못했습니다.",
            ) from exc
        if wallet.id != wallet_id:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_RESPONSE_INVALID",
                "생성된 Privy Wallet ID가 상세 조회 결과와 일치하지 않습니다.",
            )
        wallet_payload = (
            payload["data"]
            if isinstance(payload, dict) and isinstance(payload.get("data"), dict)
            else payload
        )
        if isinstance(wallet_payload, dict) and wallet_payload.get("entity") is None:
            await self._verify_wallet_owner_by_address(wallet.address, user_id)
        return wallet

    async def _verify_wallet_owner_by_address(
        self, wallet_address: str, expected_user_id: str
    ) -> None:
        headers, auth = self._request_options()
        try:
            response = await self._client.post(
                f"{self._settings.privy_api_base_url}/v1/users/wallet/address",
                headers={**headers, "Content-Type": "application/json"},
                auth=auth,
                json={"address": wallet_address},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_OWNER_LOOKUP_FAILED",
                "Privy Wallet의 사용자 소유 정보를 확인하지 못했습니다.",
            ) from exc

        owner_user_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(owner_user_id, str) or not self._same_user_id(
            owner_user_id, expected_user_id
        ):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_OWNER_INVALID",
                "Privy Wallet의 소유 사용자가 현재 인증 사용자와 다릅니다.",
            )

    @staticmethod
    def _wallet_id_from_creation_response(payload: object) -> str:
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        wallet_id = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(wallet_id, str) or not wallet_id:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_RESPONSE_INVALID",
                "Privy Wallet 생성 응답에 지갑 ID가 없습니다.",
            )
        return wallet_id

    async def _find_solana_wallet(
        self, user_id: str, external_id: str
    ) -> PrivyWalletRecord | None:
        headers, auth = self._request_options()
        try:
            response = await self._client.get(
                f"{self._settings.privy_api_base_url}/v1/wallets",
                headers=headers,
                auth=auth,
                params={
                    "user_id": user_id,
                    "chain_type": "solana",
                    "external_id": external_id,
                    "limit": 100,
                },
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
                "Privy Wallet 목록 응답에 data 배열이 없습니다.",
            )
        candidates: list[PrivyWalletRecord] = []
        for row in rows:
            if (
                not isinstance(row, dict)
                or row.get("chain_type") != "solana"
                or row.get("external_id") != external_id
            ):
                continue
            candidates.append(
                self._wallet_from_payload(
                    row,
                    user_id,
                    external_id,
                    allow_missing_owner=True,
                )
            )
        if not candidates:
            return None
        if len(candidates) > 1:
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_RESPONSE_INVALID",
                "InvoiceX 전용 Embedded Wallet이 중복 조회되었습니다.",
            )
        return await self._get_solana_wallet(candidates[0].id, user_id, external_id)

    @staticmethod
    def _wallet_from_payload(
        payload: object,
        expected_user_id: str,
        expected_external_id: str,
        *,
        allow_missing_external_id: bool = False,
        allow_missing_owner: bool = False,
    ) -> PrivyWalletRecord:
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        if not isinstance(payload, dict):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_PROVISIONING_FAILED",
                "Privy Wallet 응답이 객체 형식이 아닙니다.",
            )
        wallet_id = payload.get("id")
        address = payload.get("address")
        entity = payload.get("entity")
        response_external_id = payload.get("external_id")
        missing_fields = [
            field
            for field, value in {
                "id": wallet_id,
                "address": address,
                "chain_type": payload.get("chain_type"),
                **(
                    {}
                    if allow_missing_external_id
                    else {"external_id": response_external_id}
                ),
            }.items()
            if not isinstance(value, str) or not value
        ]
        if (
            payload.get("chain_type") != "solana"
            or (
                response_external_id != expected_external_id
                and not (allow_missing_external_id and response_external_id is None)
            )
            or missing_fields
        ):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_RESPONSE_INVALID",
                "Privy Wallet 응답의 필수 지갑 정보가 올바르지 않습니다."
                f" ({', '.join(missing_fields) or 'chain_type 또는 external_id'})",
            )
        if entity is None and allow_missing_owner:
            return PrivyWalletRecord(
                id=wallet_id, address=address, user_id=expected_user_id
            )
        if not isinstance(entity, dict):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_OWNER_INVALID",
                "Privy Wallet 응답에 사용자 소유자 정보가 없습니다.",
            )
        entity_type = entity.get("type")
        if not isinstance(entity_type, str) or entity_type.lower() != "user":
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_OWNER_INVALID",
                "Privy Wallet의 소유자 유형이 사용자 계정이 아닙니다.",
            )
        entity_user_id = entity.get("id")
        if not isinstance(entity_user_id, str) or not HttpPrivyUserGateway._same_user_id(
            entity_user_id, expected_user_id
        ):
            raise OnboardingApiError(
                status.HTTP_502_BAD_GATEWAY,
                "EMBEDDED_WALLET_OWNER_INVALID",
                "Privy Wallet의 소유 사용자가 현재 인증 사용자와 다릅니다.",
            )
        return PrivyWalletRecord(id=wallet_id, address=address, user_id=expected_user_id)

    @staticmethod
    def _same_user_id(actual: str, expected: str) -> bool:
        prefix = "did:privy:"
        normalized_actual = actual[len(prefix) :] if actual.startswith(prefix) else actual
        normalized_expected = expected[len(prefix) :] if expected.startswith(prefix) else expected
        return bool(normalized_actual) and normalized_actual == normalized_expected

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
