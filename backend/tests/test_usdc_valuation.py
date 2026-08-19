import pytest

from invoicex_backend.valuation import value_invoice_in_usdc


def test_values_usd_invoice_at_the_usdc_peg() -> None:
    valuation = value_invoice_in_usdc(invoice_amount=96_000, currency="USD")

    assert valuation.face_value_usdc == 96_000
    assert valuation.source_currency_to_usdc_rate == 1.0


def test_rejects_unsupported_currency_without_an_fx_quote() -> None:
    with pytest.raises(ValueError, match="Unsupported RWA valuation currency: KRW"):
        value_invoice_in_usdc(invoice_amount=1_000_000, currency="KRW")
