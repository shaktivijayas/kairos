from kairos import itr_export


def test_export_aggregates_business_totals_and_disallowed_cash():
    transactions = [
        {"classification": "business", "amount": 20000},
        {"classification": "business", "amount": 5000},
        {"classification": "personal", "amount": 999},
    ]
    findings = [
        {"type": "cash_limit_breach", "amount": 1000, "message": "..."},
    ]

    result = itr_export.export_itr_json(transactions, findings)

    assert result["gross_business_receipts"] == 25000
    assert result["total_business_expenses"] == 25000
    assert result["section_40A3_disallowed"] == 1000
    assert result["for_review_with_ca"] is True


def test_export_sums_deductions_by_section():
    transactions = []
    findings = [
        {"type": "deduction_opportunity", "amount": 12000, "message": "Section 80C deduction — worth reviewing"},
        {"type": "deduction_opportunity", "amount": 3000, "message": "Section 80D deduction — worth reviewing"},
        {"type": "deduction_opportunity", "amount": 8000, "message": "Section 80C deduction — worth reviewing"},
    ]

    result = itr_export.export_itr_json(transactions, findings)

    assert result["deductions_found"] == {"80C": 20000, "80D": 3000, "24b": 0}


def test_export_counts_vendor_risk_flags():
    findings = [
        {"type": "vendor_risk", "amount": None, "message": "..."},
        {"type": "vendor_risk", "amount": None, "message": "..."},
        {"type": "cash_limit_breach", "amount": 500, "message": "..."},
    ]

    result = itr_export.export_itr_json([], findings)

    assert result["vendor_risk_flags"] == 2


def test_export_handles_no_transactions_or_findings():
    result = itr_export.export_itr_json([], [])

    assert result["gross_business_receipts"] == 0
    assert result["section_40A3_disallowed"] == 0
    assert result["deductions_found"] == {"80C": 0, "80D": 0, "24b": 0}
    assert result["vendor_risk_flags"] == 0
