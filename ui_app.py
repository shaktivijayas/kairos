import uuid
from datetime import datetime, timezone

import streamlit as st

from kairos import itr_export, llm, rules, storage


def process_scanned_document(image_bytes):
    parsed = llm.read_document_image(image_bytes)
    txn = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "camera",
        "raw_text": parsed.get("category_hint") or "",
        "classification": "business",
        "amount": parsed.get("amount"),
        "payment_mode": "unknown",
        "vendor_name": parsed.get("vendor_name"),
        "vendor_gstin": parsed.get("vendor_gstin"),
        "invoice_number": parsed.get("invoice_number"),
        "category_hint": parsed.get("category_hint"),
    }

    existing = storage.load_transactions()
    findings = []

    risk_finding = rules.score_vendor_risk(existing, txn)
    if risk_finding:
        findings.append(risk_finding)

    deduction_finding = rules.find_deductions(txn)
    if deduction_finding:
        findings.append(deduction_finding)

    storage.append_transaction(txn)
    for f in findings:
        f["id"] = str(uuid.uuid4())
        f["timestamp"] = txn["timestamp"]
        f["transaction_id"] = txn["id"]
        storage.append_finding(f)

    return txn, findings


def render():
    st.set_page_config(page_title="KAIROS", layout="wide")
    tab_scan, tab_ask, tab_dashboard = st.tabs(["Scan Document", "Ask KAIROS", "Dashboard"])

    with tab_scan:
        st.write("Photograph an invoice or cash slip.")
        photo = st.camera_input("Scan document")
        if photo is not None:
            txn, findings = process_scanned_document(photo.getvalue())
            st.success(f"Recorded: {txn['vendor_name'] or 'unknown vendor'} — ₹{txn['amount']}")
            for f in findings:
                st.warning(f["message"])
                for reason in f["reasons"]:
                    st.caption(f"- {reason}")

    with tab_ask:
        question = st.text_input("Ask KAIROS: e.g. 'Should I pay this vendor in cash?'")
        if question:
            context = {
                "transactions": storage.load_transactions()[-20:],
                "findings": storage.load_findings()[-20:],
            }
            answer = llm.answer_question(question, context)
            st.info(answer)

    with tab_dashboard:
        transactions = storage.load_transactions()
        findings = storage.load_findings()
        st.subheader("Ledger")
        st.dataframe(transactions)
        st.subheader("Flags")
        st.dataframe(findings)
        if st.button("Generate ITR Export"):
            export = itr_export.export_itr_json(transactions, findings)
            st.json(export)


if __name__ == "__main__":
    render()
