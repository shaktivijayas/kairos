"""
Edge-case stress tests for kairos.rules, beyond the happy-path coverage in
test_rules.py. Several tests below (marked FIXED) originally documented real
bugs found by this file — crashes on malformed LLM output, a zero-variance
blind spot in vendor risk scoring, and keyword substring false positives in
the deduction finder — and were flipped to assert the corrected behavior once
rules.py was fixed. One test (marked LIMITATION) documents a gap that's
intentionally not fixed, with the reasoning inline.
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


# --- fixed bugs / gaps -------------------------------------------------------

def test_cash_limit_missing_amount_skips_gracefully():
    """
    FIXED: new_txn.get("amount") is now validated as numeric before use. If
    the LLM fails to extract an amount from an SMS (returns null), the
    transaction is skipped for this check instead of crashing the request
    with a TypeError.
    """
    new_txn = _txn(amount=None)
    assert rules.check_cash_limit([], new_txn, limit=10000) is None


def test_cash_limit_missing_timestamp_skips_gracefully():
    """
    FIXED: a missing/falsy timestamp is now treated as "can't determine the
    date" and the check is skipped, instead of raising KeyError.
    """
    new_txn = _txn()
    del new_txn["timestamp"]
    assert rules.check_cash_limit([], new_txn, limit=10000) is None


def test_cash_limit_string_amount_skips_gracefully():
    """
    FIXED: a non-numeric amount (e.g. a string from a JSON quirk in the LLM
    response) is now rejected up front rather than crashing when summed
    against prior numeric amounts.
    """
    existing = [_txn(amount=5000)]
    new_txn = _txn(amount="6000")
    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_cash_limit_malformed_prior_entry_is_skipped_not_fatal():
    """
    FIXED: a malformed prior transaction (bad amount type) in the existing
    ledger no longer crashes the whole aggregation — it's excluded from the
    sum and the rest of the check proceeds normally.
    """
    existing = [_txn(amount="bad-data"), _txn(amount=6000)]
    new_txn = _txn(amount=5000)
    finding = rules.check_cash_limit(existing, new_txn, limit=10000)
    assert finding is not None
    assert finding["amount"] == 1000  # only the valid 6000 + 5000 combine


def test_cash_limit_different_unknown_vendors_no_longer_combine():
    """
    FIXED: two cash transactions with vendor_name=None (unrecognized
    vendor) are no longer grouped together just because None == None —
    _same_vendor requires an actual matching GSTIN or vendor name, so two
    genuinely unrelated unnamed-vendor payments can no longer trip a false
    breach together.
    """
    existing = [_txn(amount=6000, vendor_name=None)]
    new_txn = _txn(amount=5000, vendor_name=None)
    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_cash_limit_differently_cased_vendor_names_now_combine():
    """
    FIXED: vendor name matching is now case-insensitive (normalized via
    strip().lower()), so "Sharma Traders" from an invoice and
    "sharma traders" from an SMS are recognized as the same vendor and a
    real breach is no longer missed.
    """
    existing = [_txn(amount=8000, vendor_name="Sharma Traders")]
    new_txn = _txn(amount=5000, vendor_name="sharma traders")
    finding = rules.check_cash_limit(existing, new_txn, limit=10000)
    assert finding is not None
    assert finding["amount"] == 3000


def test_cash_limit_same_gstin_different_vendor_spelling_combines():
    """
    New coverage for the GSTIN-based matching path: a vendor whose name is
    OCR'd slightly differently between two invoices, but shares a GSTIN,
    should still be recognized as the same vendor for aggregation.
    """
    existing = [_txn(amount=8000, vendor_name="Sharma Trader's", vendor_gstin="27AAAAA0000A1Z5")]
    new_txn = _txn(amount=5000, vendor_name="Sharma Traders Pvt", vendor_gstin="27AAAAA0000A1Z5")
    finding = rules.check_cash_limit(existing, new_txn, limit=10000)
    assert finding is not None
    assert finding["amount"] == 3000


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


# --- fixed bugs / gaps -------------------------------------------------------

def test_vendor_risk_zero_variance_history_now_flagged():
    """
    FIXED: when a vendor's prior invoices are identical (stdev == 0), the
    deviation check now falls back to a relative-jump comparison (>50% off
    the constant historical mean) instead of skipping entirely — so a
    wildly anomalous new amount (100x a vendor's stable history) is caught.
    """
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=1000),
    ]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-3", amount=100000)
    finding = rules.score_vendor_risk(existing, new_txn)
    assert finding is not None
    assert any("deviates sharply" in r for r in finding["reasons"])


def test_vendor_risk_zero_variance_small_fluctuation_not_flagged():
    """
    Companion boundary test for the fix above: a modest fluctuation from a
    zero-variance history (well under the 50% relative threshold) should
    still pass quietly rather than over-flagging routine variation.
    """
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=1000),
    ]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-3", amount=1200)
    assert rules.score_vendor_risk(existing, new_txn) is None


def test_vendor_risk_lowercase_gstin_no_longer_flagged_as_malformed():
    """
    FIXED: GSTIN format matching now normalizes to uppercase before
    checking, so a structurally valid GSTIN captured in lowercase (common
    after OCR on a photographed invoice) is no longer flagged as malformed.
    """
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="27aaaaa0000a1z5"))
    assert finding is None


def test_vendor_risk_structurally_valid_but_fabricated_gstin_not_flagged():
    """
    LIMITATION (intentionally not fixed): the format regex checks shape
    only, not the real GSTIN checksum or GSTN allotment. A well-formed but
    entirely fabricated GSTIN passes silently. A real checksum algorithm
    exists (mod-36/ISO-7064-based) but implementing it from memory risks
    getting it subtly wrong — rejecting real GSTINs is worse for user trust
    than not catching fabricated ones, given KAIROS already has no GSTN
    portal access to verify allotment either way. Left as a documented
    ceiling rather than a guessed implementation.
    """
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="12ABCDE1234F1Z9"))
    assert finding is None


def test_vendor_risk_duplicate_check_now_matches_via_gstin_when_vendor_missing():
    """
    FIXED: duplicate-invoice detection now matches on GSTIN when both
    transactions have one (more reliable than vendor_name), so it no longer
    silently skips the noisiest, highest-risk data — transactions where the
    vendor name wasn't captured but the GSTIN was.
    """
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", vendor_name=None, invoice_number="INV-1"),
    ]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", vendor_name=None, invoice_number="INV-1")
    finding = rules.score_vendor_risk(existing, new_txn)
    assert finding is not None
    assert any("already seen" in r for r in finding["reasons"])


def test_vendor_risk_duplicate_check_still_skipped_when_both_gstin_and_vendor_missing():
    """
    Companion boundary test: when NEITHER GSTIN nor vendor_name is present
    on either side, there's no reliable identity signal at all, so the
    duplicate check correctly stays silent rather than guessing.
    """
    existing = [_txn(vendor_gstin=None, vendor_name=None, invoice_number="INV-1")]
    new_txn = _txn(vendor_gstin=None, vendor_name=None, invoice_number="INV-1")
    finding = rules.score_vendor_risk(existing, new_txn)
    # missing GSTIN still fires its own reason; the duplicate-invoice
    # reason specifically must not, since there's no identity to match on
    assert finding is not None
    assert not any("already seen" in r for r in finding["reasons"])


# ---------------------------------------------------------------------------
# find_deductions — boundary conditions
# ---------------------------------------------------------------------------

def test_find_deductions_matches_at_start_and_end_of_text():
    assert rules.find_deductions(_txn(raw_text="LIC")) != []
    assert rules.find_deductions(_txn(raw_text="Paid for home loan")) != []


def test_find_deductions_case_and_punctuation_insensitive():
    findings = rules.find_deductions(_txn(raw_text="LIC. Premium-payment!!"))
    assert len(findings) == 1
    assert "80C" in findings[0]["message"]


def test_find_deductions_reads_category_hint_when_raw_text_empty():
    findings = rules.find_deductions(_txn(raw_text="", category_hint="Health Insurance premium"))
    assert len(findings) == 1
    assert "80D" in findings[0]["message"]


def test_find_deductions_none_amount_does_not_crash():
    findings = rules.find_deductions(_txn(raw_text="LIC premium", amount=None))
    assert len(findings) == 1
    assert findings[0]["amount"] is None


# --- fixed bugs / gaps -------------------------------------------------------

def test_find_deductions_premium_no_longer_false_positives_to_24b():
    """
    FIXED: keyword matching now requires word boundaries (\\bkeyword\\b), so
    "premium" no longer accidentally matches the substring "emi" (pr-EMI-um)
    and misfires a Section 24b (home loan EMI) suggestion.
    """
    assert rules.find_deductions(_txn(raw_text="Paid two-wheeler premium today")) == []


def test_find_deductions_policy_no_longer_false_positives_to_80c():
    """
    FIXED: same fix closes the "policy" -> "lic" collision (po-LIC-y) — a
    vehicle/fire/travel insurance policy no longer gets misfiled as a
    Section 80C LIC deduction.
    """
    assert rules.find_deductions(_txn(raw_text="Renewed two-wheeler insurance policy")) == []


def test_find_deductions_chemical_no_longer_false_positives_to_24b():
    """
    FIXED: same word-boundary fix closes the "chemical" -> "emi" collision.
    """
    assert rules.find_deductions(_txn(raw_text="Chemical supplies for manufacturing unit")) == []


def test_find_deductions_genuine_word_boundary_matches_still_work():
    """
    Companion sanity check for the word-boundary fix: real standalone
    keyword usage — including immediately after punctuation — still
    matches correctly, so the fix didn't overcorrect into false negatives.
    """
    assert rules.find_deductions(_txn(raw_text="EMI due tomorrow")) != []
    assert rules.find_deductions(_txn(raw_text="Bought a new insurance policy: mediclaim")) != []


def test_find_deductions_now_returns_all_matching_sections():
    """
    FIXED: find_deductions now returns a list of every matching section
    instead of stopping at the first — a transaction that legitimately
    touches two different deduction sections surfaces both instead of
    silently dropping the second.
    """
    findings = rules.find_deductions(
        _txn(raw_text="LIC premium and home loan EMI both paid this month")
    )
    sections = {f["message"] for f in findings}
    assert len(findings) == 2
    assert any("80C" in s for s in sections)
    assert any("24b" in s for s in sections)


def test_find_deductions_does_not_duplicate_within_the_same_section():
    """
    A transaction matching two keywords from the SAME section (e.g. both
    "home loan" and "emi") should still only produce one finding for that
    section, not one per matched keyword.
    """
    findings = rules.find_deductions(_txn(raw_text="Home loan EMI debited"))
    assert len(findings) == 1
    assert "24b" in findings[0]["message"]
