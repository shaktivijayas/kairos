import re

GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][0-9A-Z]$")

DEDUCTION_KEYWORDS = {
    "80C": ["lic", "life insurance", "ppf", "elss", "mutual fund", "tuition fee"],
    "80D": ["health insurance", "mediclaim", "medical insurance"],
    "24b": ["home loan", "housing loan", "emi"],
}

DEDUCTION_PATTERNS = {
    section: [(kw, re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)) for kw in keywords]
    for section, keywords in DEDUCTION_KEYWORDS.items()
}


def _normalize_vendor(name):
    if not isinstance(name, str):
        return None
    normalized = name.strip().lower()
    return normalized or None


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _same_vendor(a, b):
    """
    Two transactions are the same vendor if they share a GSTIN (when both
    have one — the more reliable signal), otherwise if they share a
    normalized vendor name. Two transactions with neither a GSTIN nor a
    vendor name are never considered the same vendor — there's no reliable
    signal to group them on, and guessing would create false positives.
    """
    a_gstin, b_gstin = a.get("vendor_gstin"), b.get("vendor_gstin")
    if a_gstin and b_gstin:
        return a_gstin.strip().upper() == b_gstin.strip().upper()
    a_vendor = _normalize_vendor(a.get("vendor_name"))
    b_vendor = _normalize_vendor(b.get("vendor_name"))
    return a_vendor is not None and a_vendor == b_vendor


def check_cash_limit(transactions, new_txn, limit):
    if new_txn.get("payment_mode") != "cash" or new_txn.get("classification") != "business":
        return None

    amount = new_txn.get("amount")
    if not _is_number(amount):
        return None

    timestamp = new_txn.get("timestamp")
    if not timestamp:
        return None
    date = timestamp[:10]

    vendor = new_txn.get("vendor_name")
    total = amount

    for t in transactions:
        if (
            t.get("payment_mode") == "cash"
            and t.get("classification") == "business"
            and t.get("timestamp", "")[:10] == date
            and _same_vendor(new_txn, t)
        ):
            t_amount = t.get("amount")
            if _is_number(t_amount):
                total += t_amount

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
    elif not GSTIN_PATTERN.match(gstin.strip().upper()):
        reasons.append(f"GSTIN '{gstin}' does not match the standard 15-character format")

    vendor = new_txn.get("vendor_name")
    invoice_number = new_txn.get("invoice_number")

    if invoice_number:
        for t in transactions:
            if _same_vendor(new_txn, t) and t.get("invoice_number") == invoice_number:
                reasons.append(
                    f"Invoice number '{invoice_number}' already seen for vendor '{vendor or 'unknown'}'"
                )
                break

    prior_amounts = [
        t["amount"] for t in transactions
        if _same_vendor(new_txn, t) and _is_number(t.get("amount"))
    ]
    amount = new_txn.get("amount")
    if len(prior_amounts) >= 2 and _is_number(amount):
        mean = sum(prior_amounts) / len(prior_amounts)
        variance = sum((a - mean) ** 2 for a in prior_amounts) / len(prior_amounts)
        stdev = variance ** 0.5
        if stdev > 0:
            deviates = abs(amount - mean) > 2 * stdev
        else:
            # No historical variance to compare against — fall back to a
            # relative-jump check so an identical-invoice vendor whose next
            # amount is wildly different doesn't slip through undetected.
            deviates = mean > 0 and abs(amount - mean) > mean * 0.5
        if deviates:
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


def find_deductions(new_txn):
    text = f"{new_txn.get('raw_text') or ''} {new_txn.get('category_hint') or ''}"
    findings = []
    for section, patterns in DEDUCTION_PATTERNS.items():
        for kw, pattern in patterns:
            if pattern.search(text):
                findings.append({
                    "type": "deduction_opportunity",
                    "severity": "green",
                    "amount": new_txn.get("amount"),
                    "message": (
                        f"This looks like it may qualify for a Section {section} deduction "
                        "— worth reviewing with your CA."
                    ),
                    "reasons": [f"Matched keyword '{kw}' under Section {section}"],
                })
                break
    return findings
