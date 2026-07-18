import re

GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][0-9A-Z]$")


def check_cash_limit(transactions, new_txn, limit):
    if new_txn.get("payment_mode") != "cash" or new_txn.get("classification") != "business":
        return None

    vendor = new_txn.get("vendor_name")
    date = new_txn["timestamp"][:10]
    total = new_txn["amount"]

    for t in transactions:
        if (
            t.get("payment_mode") == "cash"
            and t.get("classification") == "business"
            and t.get("vendor_name") == vendor
            and t.get("timestamp", "")[:10] == date
        ):
            total += t["amount"]

    if total > limit:
        return {
            "type": "cash_limit_breach",
            "severity": "red",
            "amount": total - limit,
            "message": (
                f"Cash payments to {vendor or 'this vendor'} on {date} total "
                f"₹{total:.2f}, over the ₹{limit} daily limit under Section 40A(3)."
            ),
            "reasons": [
                f"₹{total:.2f} paid in cash to {vendor or 'unknown vendor'} on {date}",
                f"Section 40A(3) disallows cash business expenditure over ₹{limit}/day to a single person",
            ],
        }
    return None


def score_vendor_risk(transactions, new_txn):
    reasons = []
    gstin = new_txn.get("vendor_gstin")
    if not gstin:
        reasons.append("No GSTIN captured on this invoice")
    elif not GSTIN_PATTERN.match(gstin):
        reasons.append(f"GSTIN '{gstin}' does not match the standard 15-character format")

    invoice_number = new_txn.get("invoice_number")
    vendor = new_txn.get("vendor_name")
    if invoice_number and vendor:
        for t in transactions:
            if t.get("vendor_name") == vendor and t.get("invoice_number") == invoice_number:
                reasons.append(f"Invoice number '{invoice_number}' already seen for vendor '{vendor}'")
                break

    if vendor:
        prior_amounts = [
            t["amount"] for t in transactions
            if t.get("vendor_name") == vendor and t.get("amount") is not None
        ]
        if len(prior_amounts) >= 2:
            mean = sum(prior_amounts) / len(prior_amounts)
            variance = sum((a - mean) ** 2 for a in prior_amounts) / len(prior_amounts)
            stdev = variance ** 0.5
            amount = new_txn.get("amount")
            if stdev > 0 and amount is not None and abs(amount - mean) > 2 * stdev:
                reasons.append(
                    f"Amount ₹{amount:.2f} deviates sharply from this vendor's usual ₹{mean:.2f}"
                )

    if not reasons:
        return None

    severity = "red" if len(reasons) >= 2 else "yellow"
    return {
        "type": "vendor_risk",
        "severity": severity,
        "amount": None,
        "message": f"Vendor '{vendor or 'unknown'}' flagged as {severity} risk for ITC purposes.",
        "reasons": reasons,
    }
