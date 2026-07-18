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
