"""
Edge-case stress tests for kairos.rules, beyond the happy-path coverage in
test_rules.py. Some tests here assert CURRENT (buggy or limited) behavior on
purpose, with a docstring explaining the gap — they exist to make the gap
visible and regression-proof the decision once it's addressed, not because
the behavior is desirable.
"""
import pytest

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


# ---------------------------------------------------------------------------
# check_cash_limit — boundary conditions
# ---------------------------------------------------------------------------

def test_cash_limit_exactly_at_boundary_is_not_a_breach():
    new_txn = _txn(amount=10000)
    assert rules.check_cash_limit([], new_txn, limit=10000) is None


def test_cash_limit_one_rupee_over_boundary_breaches():
    new_txn = _txn(amount=10001)
    finding = rules.check_cash_limit([], new_txn, limit=10000)
    assert finding is not None
    assert finding["amount"] == 1


def test_cash_limit_zero_limit_flags_any_cash_business_txn():
    new_txn = _txn(amount=1)
    finding = rules.check_cash_limit([], new_txn, limit=0)
    assert finding is not None
    assert finding["amount"] == 1


def test_cash_limit_aggregates_across_three_prior_transactions():
    existing = [_txn(amount=3000), _txn(amount=3000), _txn(amount=3000)]
    new_txn = _txn(amount=2000)
    finding = rules.check_cash_limit(existing, new_txn, limit=10000)
    assert finding is not None
    assert finding["amount"] == 1000  # 11000 - 10000


def test_cash_limit_floating_point_paise_amounts_breach_correctly():
    existing = [_txn(amount=3333.33), _txn(amount=3333.33), _txn(amount=3333.33)]
    new_txn = _txn(amount=0.02)
    finding = rules.check_cash_limit(existing, new_txn, limit=10000)
    assert finding is not None
    assert finding["amount"] == pytest.approx(0.01, abs=1e-6)


def test_cash_limit_only_matching_vendor_combines_among_several():
    existing = [
        _txn(amount=4000, vendor_name="Vendor A"),
        _txn(amount=4000, vendor_name="Vendor B"),
        _txn(amount=4000, vendor_name="Sharma Traders"),
    ]
    new_txn = _txn(amount=7000, vendor_name="Sharma Traders")
    finding = rules.check_cash_limit(existing, new_txn, limit=10000)
    assert finding is not None
    assert finding["amount"] == 1000  # only the 4000 + 7000 Sharma Traders pair


# --- bugs / gaps surfaced by boundary testing -------------------------------

def test_cash_limit_missing_amount_crashes_instead_of_skipping():
    """
    BUG: new_txn["amount"] is accessed with direct indexing, not .get(). If
    the LLM fails to extract an amount from an SMS (returns null), this
    raises TypeError instead of skipping the transaction gracefully — a
    malformed upstream LLM response can crash the whole webhook request.
    """
    new_txn = _txn(amount=None)
    with pytest.raises(TypeError):
        rules.check_cash_limit([], new_txn, limit=10000)


def test_cash_limit_missing_timestamp_key_raises_keyerror():
    """
    BUG: new_txn["timestamp"] is accessed with direct indexing. If the
    caller ever omits the key entirely (vs. an empty string), this crashes
    with KeyError rather than being treated as "unknown date".
    """
    new_txn = _txn()
    del new_txn["timestamp"]
    with pytest.raises(KeyError):
        rules.check_cash_limit([], new_txn, limit=10000)


def test_cash_limit_string_amount_crashes_during_aggregation():
    """
    BUG: if amount arrives as a string (e.g. a JSON quirk from the LLM
    response), summing against prior numeric amounts raises TypeError
    instead of coercing or rejecting cleanly.
    """
    existing = [_txn(amount=5000)]
    new_txn = _txn(amount="6000")
    with pytest.raises(TypeError):
        rules.check_cash_limit(existing, new_txn, limit=10000)


def test_cash_limit_different_unknown_vendors_incorrectly_combine():
    """
    GAP: two cash transactions with vendor_name=None (unrecognized vendor,
    common from noisy SMS/OCR) are grouped together as if they were the same
    vendor purely because None == None. Two genuinely unrelated small cash
    payments to different unnamed parties can trip a false breach.
    """
    existing = [_txn(amount=6000, vendor_name=None)]
    new_txn = _txn(amount=5000, vendor_name=None)
    finding = rules.check_cash_limit(existing, new_txn, limit=10000)
    assert finding is not None  # documents the false-positive-prone behavior


def test_cash_limit_differently_cased_vendor_names_do_not_combine():
    """
    GAP (false negative): vendor name matching is exact-string, case
    sensitive. The same vendor captured as "Sharma Traders" from an invoice
    and "sharma traders" from an SMS won't be recognized as the same vendor,
    so a real breach can be missed.
    """
    existing = [_txn(amount=8000, vendor_name="Sharma Traders")]
    new_txn = _txn(amount=5000, vendor_name="sharma traders")
    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


# ---------------------------------------------------------------------------
# score_vendor_risk — boundary conditions
# ---------------------------------------------------------------------------

def test_vendor_risk_empty_string_gstin_treated_as_missing():
    finding = rules.score_vendor_risk([], _txn(vendor_gstin=""))
    assert finding is not None
    assert "No GSTIN captured" in finding["reasons"][0]


def test_vendor_risk_deviation_not_flagged_exactly_at_two_stdev_boundary():
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=3000),
    ]
    # mean=2000, stdev=1000, so amount=4000 is exactly 2*stdev away — not > threshold
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-3", amount=4000)
    assert rules.score_vendor_risk(existing, new_txn) is None


def test_vendor_risk_deviation_flagged_just_past_two_stdev_boundary():
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=3000),
    ]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-3", amount=4001)
    finding = rules.score_vendor_risk(existing, new_txn)
    assert finding is not None
    assert any("deviates sharply" in r for r in finding["reasons"])


def test_vendor_risk_three_reasons_fire_together_and_severity_is_red():
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="DUPE"),
    ]
    new_txn = _txn(vendor_gstin=None, invoice_number="DUPE", amount=90000)
    finding = rules.score_vendor_risk(existing, new_txn)
    assert finding is not None
    assert finding["severity"] == "red"
    assert len(finding["reasons"]) == 3


def test_vendor_risk_prior_amounts_ignore_entries_missing_amount():
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=None),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-3", amount=1100),
    ]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-4", amount=1050)
    # only 2 valid prior amounts (1000, 1100) feed mean/stdev; 1050 is unremarkable
    assert rules.score_vendor_risk(existing, new_txn) is None


# --- bugs / gaps surfaced by boundary testing -------------------------------

def test_vendor_risk_zero_variance_history_blind_spot():
    """
    BUG: when a vendor's prior invoices happen to be identical (stdev == 0),
    the deviation check is gated on `stdev > 0` and skips entirely — so a
    wildly anomalous new amount (100x a vendor's stable history) goes
    completely undetected, which is exactly the scenario the check exists
    to catch.
    """
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=1000),
    ]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-3", amount=100000)
    assert rules.score_vendor_risk(existing, new_txn) is None  # documents the blind spot


def test_vendor_risk_lowercase_gstin_flagged_as_malformed():
    """
    GAP (likely false positive): the GSTIN regex requires uppercase letters.
    A structurally valid GSTIN captured in lowercase (common after OCR on a
    photographed invoice) is flagged as malformed even though it's real.
    """
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="27aaaaa0000a1z5"))
    assert finding is not None
    assert any("does not match" in r for r in finding["reasons"])


def test_vendor_risk_structurally_valid_but_fabricated_gstin_not_flagged():
    """
    LIMITATION (by design, not a bug): the format regex checks shape only,
    not the real GSTIN checksum or GSTN allotment. A well-formed but
    entirely fabricated GSTIN passes silently. This is a ceiling on the
    check's accuracy given KAIROS has no GSTN portal access by design.
    """
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="12ABCDE1234F1Z9"))
    assert finding is None


def test_vendor_risk_duplicate_check_skipped_when_vendor_name_missing():
    """
    GAP: duplicate-invoice detection requires both invoice_number AND
    vendor_name to be truthy. Transactions with no recognized vendor name
    (exactly the noisiest, highest-risk data) silently skip this check.
    """
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", vendor_name=None, invoice_number="INV-1"),
    ]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", vendor_name=None, invoice_number="INV-1")
    assert rules.score_vendor_risk(existing, new_txn) is None


# ---------------------------------------------------------------------------
# find_deductions — boundary conditions
# ---------------------------------------------------------------------------

def test_find_deductions_matches_at_start_and_end_of_text():
    assert rules.find_deductions(_txn(raw_text="LIC")) is not None
    assert rules.find_deductions(_txn(raw_text="Paid for home loan")) is not None


def test_find_deductions_case_and_punctuation_insensitive():
    finding = rules.find_deductions(_txn(raw_text="LIC. Premium-payment!!"))
    assert finding is not None
    assert "80C" in finding["message"]


def test_find_deductions_reads_category_hint_when_raw_text_empty():
    finding = rules.find_deductions(_txn(raw_text="", category_hint="Health Insurance premium"))
    assert finding is not None
    assert "80D" in finding["message"]


def test_find_deductions_none_amount_does_not_crash():
    finding = rules.find_deductions(_txn(raw_text="LIC premium", amount=None))
    assert finding is not None
    assert finding["amount"] is None


# --- bugs / gaps surfaced by boundary testing -------------------------------

def test_find_deductions_false_positive_on_premium_substring():
    """
    BUG: keyword matching is plain substring search with no word boundaries.
    "premium" contains the literal substring "emi" (pr-EMI-um), so any
    insurance-premium text with no other keyword incorrectly surfaces a
    Section 24b (home loan EMI) deduction — exactly the kind of confident,
    wrong suggestion the product pitch promises never to make.
    """
    finding = rules.find_deductions(_txn(raw_text="Paid two-wheeler premium today"))
    assert finding is not None
    assert "24b" in finding["message"]  # wrong: this transaction has nothing to do with a home loan


def test_find_deductions_false_positive_on_policy_substring():
    """
    BUG: distinct collision found while writing the test above — "policy"
    contains the literal substring "lic" (po-LIC-y), so ANY transaction
    mentioning a policy (vehicle, fire, travel — not life insurance) gets
    misfiled as a Section 80C (LIC) deduction. This one is worse than the
    "emi" collision because "policy" is an extremely common word in
    non-tax-relevant purchase text.
    """
    finding = rules.find_deductions(_txn(raw_text="Renewed two-wheeler insurance policy"))
    assert finding is not None
    assert "80C" in finding["message"]  # wrong: vehicle insurance is not a Section 80C LIC deduction


def test_find_deductions_false_positive_on_chemical_substring():
    """
    BUG: same root cause as above via a different everyday word — "chemical"
    also contains "emi" (che-MI-cal... c-h-E-M-I-cal), so ordinary business
    purchases with no loan/insurance relevance can misfire.
    """
    finding = rules.find_deductions(_txn(raw_text="Chemical supplies for manufacturing unit"))
    assert finding is not None
    assert "24b" in finding["message"]  # wrong: no loan or EMI involved


def test_find_deductions_only_returns_first_match_when_multiple_qualify():
    """
    GAP: a transaction that legitimately touches two different deduction
    sections only ever surfaces the first one found (dict iteration order:
    80C, 80D, 24b) — the second, equally valid opportunity is silently
    dropped, understating "found money" for the user.
    """
    finding = rules.find_deductions(
        _txn(raw_text="LIC premium and home loan EMI both paid this month")
    )
    assert finding is not None
    assert "80C" in finding["message"]  # the 24b home-loan angle is never surfaced
