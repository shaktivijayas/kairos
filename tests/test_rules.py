from kairos import rules


def _txn(**overrides):
    base = {
        "amount": 5000,
        "classification": "business",
        "payment_mode": "cash",
        "vendor_name": "Sharma Traders",
        "vendor_gstin": None,
        "invoice_number": None,
        "raw_text": "",
        "category_hint": None,
        "timestamp": "2026-07-18T10:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_cash_limit_breach_when_same_day_same_vendor_total_exceeds_limit():
    existing = [_txn(amount=6000)]
    new_txn = _txn(amount=5000)

    finding = rules.check_cash_limit(existing, new_txn, limit=10000)

    assert finding is not None
    assert finding["type"] == "cash_limit_breach"
    assert finding["severity"] == "red"
    assert finding["amount"] == 1000  # 11000 total - 10000 limit
    assert "Sharma Traders" in finding["message"]
    assert len(finding["reasons"]) == 2


def test_no_breach_when_under_limit():
    existing = [_txn(amount=2000)]
    new_txn = _txn(amount=3000)

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_no_breach_for_non_cash_payment():
    existing = [_txn(amount=8000)]
    new_txn = _txn(amount=5000, payment_mode="upi")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_no_breach_for_personal_classification():
    existing = [_txn(amount=8000, classification="personal")]
    new_txn = _txn(amount=5000, classification="personal")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_different_vendors_do_not_combine():
    existing = [_txn(amount=8000, vendor_name="Other Vendor")]
    new_txn = _txn(amount=5000, vendor_name="Sharma Traders")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_different_day_does_not_combine():
    existing = [_txn(amount=8000, timestamp="2026-07-17T10:00:00+00:00")]
    new_txn = _txn(amount=5000, timestamp="2026-07-18T10:00:00+00:00")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None
