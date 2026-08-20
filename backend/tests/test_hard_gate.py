from invoicex_backend.hard_gate import HardGateInput, evaluate_hard_gate


def _eligible(**overrides: bool) -> HardGateInput:
    values = {
        "buyer_confirmed": True,
        "supplier_verified": True,
        "buyer_verified": True,
        "delivery_completed": True,
        "dispute_free": True,
        "not_overdue": True,
        "prior_assignment_free": True,
        "sanctions_clear": True,
    }
    values.update(overrides)
    return HardGateInput(**values)


def test_hard_gate_passes_only_when_all_eight_checks_pass() -> None:
    result = evaluate_hard_gate(_eligible())

    assert result.passed is True
    assert len(result.checks) == 8
    assert all(check.passed for check in result.checks)
    assert result.failure_reasons == []


def test_hard_gate_reports_each_failed_condition_without_scoring() -> None:
    result = evaluate_hard_gate(
        _eligible(delivery_completed=False, sanctions_clear=False)
    )

    assert result.passed is False
    assert {check.key for check in result.checks if not check.passed} == {
        "DELIVERY_COMPLETED",
        "SANCTIONS_CLEAR",
    }
    assert len(result.failure_reasons) == 2
