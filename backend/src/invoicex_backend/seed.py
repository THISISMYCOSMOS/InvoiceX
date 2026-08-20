"""Fixed demo identities and investment-criteria reference data.

These are intentionally source-controlled demo records, not user-managed
production accounts. Their passwords are validated only by the GCP demo API;
the frontend never needs to embed them when using the real backend.
"""

from __future__ import annotations

from dataclasses import dataclass

from invoicex_backend.models import InvestmentCriteriaBuyer, LoginRole


@dataclass(frozen=True, slots=True)
class DemoAccount:
    role: LoginRole
    email: str
    password: str


DEMO_ACCOUNTS: tuple[DemoAccount, ...] = (
    DemoAccount(LoginRole.SUPPLIER, "supplier@company.com", "supplier"),
    DemoAccount(LoginRole.BUYER, "buyer@company.com", "buyer"),
    DemoAccount(LoginRole.INVESTOR, "investor@company.com", "investor"),
)

INVESTMENT_CRITERIA_BUYERS: tuple[InvestmentCriteriaBuyer, ...] = (
    InvestmentCriteriaBuyer(id="BUYER_PRIME", name="Prime Mobility"),
    InvestmentCriteriaBuyer(id="BUYER_ORBIT", name="Orbit Components"),
    InvestmentCriteriaBuyer(id="BUYER_DAON", name="Daon Logistics"),
    InvestmentCriteriaBuyer(id="BUYER_VERTEX", name="Vertex Retail"),
    InvestmentCriteriaBuyer(id="BUYER_HALCYON", name="Halcyon Robotics Ltd"),
)


def authenticate_demo_account(role: LoginRole, email: str, password: str) -> DemoAccount | None:
    normalized_email = email.strip().lower()
    return next(
        (
            account
            for account in DEMO_ACCOUNTS
            if account.role == role
            and account.email == normalized_email
            and account.password == password
        ),
        None,
    )
