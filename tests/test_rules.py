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


def test_vendor_risk_flags_missing_gstin():
    finding = rules.score_vendor_risk([], _txn(vendor_gstin=None))

    assert finding is not None
    assert finding["type"] == "vendor_risk"
    assert finding["severity"] == "yellow"
    assert "No GSTIN captured" in finding["reasons"][0]


def test_vendor_risk_flags_malformed_gstin():
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="NOT-A-GSTIN"))

    assert finding is not None
    assert any("does not match" in r for r in finding["reasons"])


def test_vendor_risk_passes_valid_gstin_with_no_history():
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="27AAAAA0000A1Z5"))

    assert finding is None


def test_vendor_risk_flags_duplicate_invoice_number():
    existing = [_txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-100")]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-100")

    finding = rules.score_vendor_risk(existing, new_txn)

    assert finding is not None
    assert any("already seen" in r for r in finding["reasons"])


def test_vendor_risk_flags_amount_deviation_and_escalates_severity():
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=1100),
    ]
    new_txn = _txn(vendor_gstin=None, invoice_number="INV-3", amount=50000)

    finding = rules.score_vendor_risk(existing, new_txn)

    assert finding is not None
    assert finding["severity"] == "red"  # missing GSTIN + amount deviation = 2 reasons
    assert any("deviates sharply" in r for r in finding["reasons"])


def test_find_deductions_matches_80c_keyword():
    finding = rules.find_deductions(_txn(raw_text="LIC premium payment", amount=12000))

    assert finding is not None
    assert finding["type"] == "deduction_opportunity"
    assert "80C" in finding["message"]
    assert finding["amount"] == 12000


def test_find_deductions_matches_80d_keyword():
    finding = rules.find_deductions(_txn(category_hint="health insurance renewal"))

    assert finding is not None
    assert "80D" in finding["message"]


def test_find_deductions_matches_24b_keyword():
    finding = rules.find_deductions(_txn(raw_text="Home loan EMI debited"))

    assert finding is not None
    assert "24b" in finding["message"]


def test_find_deductions_returns_none_when_no_keyword_matches():
    assert rules.find_deductions(_txn(raw_text="Paid for office chairs")) is None
