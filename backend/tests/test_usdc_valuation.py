import pytest

from invoicex_backend.valuation import value_invoice_in_usdc


def test_values_usd_invoice_at_the_usdc_peg() -> None:
    valuation = value_invoice_in_usdc(invoice_amount=96_000, currency="USD")

    assert valuation.face_value_usdc == 96_000
    assert valuation.source_currency_to_usdc_rate == 1.0


@pytest.mark.parametrize(
    ("invoice_amount", "expected_base_units"),
    [("5", 5_000_000), ("5.25", 5_250_000), ("5.000001", 5_000_001)],
)
def test_document_amount_reaches_valuation_as_exact_base_units(
    invoice_amount: str, expected_base_units: int
) -> None:
    valuation = value_invoice_in_usdc(invoice_amount=invoice_amount, currency="USDC")
    assert valuation.face_value_base_units == expected_base_units


@pytest.mark.parametrize("invoice_amount", ["5.0000001", "NaN", "0", "-1"])
def test_document_amount_is_not_silently_rounded_or_defaulted(invoice_amount: str) -> None:
    with pytest.raises(ValueError):
        value_invoice_in_usdc(invoice_amount=invoice_amount, currency="USDC")


def test_rejects_unsupported_currency_without_an_fx_quote() -> None:
    with pytest.raises(ValueError, match="Unsupported RWA valuation currency: KRW"):
        value_invoice_in_usdc(invoice_amount=1_000_000, currency="KRW")
