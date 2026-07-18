def export_itr_json(transactions, findings):
    business_txns = [t for t in transactions if t.get("classification") == "business"]
    gross_receipts = sum(
        t.get("amount") or 0 for t in business_txns if (t.get("amount") or 0) > 0
    )
    total_expenses = sum(t.get("amount") or 0 for t in business_txns)

    disallowed_40a3 = sum(
        f["amount"] for f in findings
        if f["type"] == "cash_limit_breach" and f.get("amount")
    )

    deductions_by_section = {"80C": 0.0, "80D": 0.0, "24b": 0.0}
    for f in findings:
        if f["type"] == "deduction_opportunity" and f.get("amount"):
            for section in deductions_by_section:
                if f"Section {section}" in f["message"]:
                    deductions_by_section[section] += f["amount"]

    vendor_risk_count = sum(1 for f in findings if f["type"] == "vendor_risk")

    return {
        "gross_business_receipts": round(gross_receipts, 2),
        "total_business_expenses": round(total_expenses, 2),
        "section_40A3_disallowed": round(disallowed_40a3, 2),
        "deductions_found": {k: round(v, 2) for k, v in deductions_by_section.items()},
        "vendor_risk_flags": vendor_risk_count,
        "for_review_with_ca": True,
    }
