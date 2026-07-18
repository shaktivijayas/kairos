import uuid
from datetime import datetime, timezone

import streamlit as st

from kairos import itr_export, llm, profile, rules, storage


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

    if profile.load_profile().get("tax_scheme") != "composition":
        risk_finding = rules.score_vendor_risk(existing, txn)
        if risk_finding:
            findings.append(risk_finding)

    findings.extend(rules.find_deductions(txn))

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
            with st.spinner("Analyzing document..."):
                try:
                    txn, findings = process_scanned_document(photo.getvalue())
                except Exception:
                    st.error("⚠️ Document scan unresolved.")
                    st.info(
                        "KAIROS couldn't read this snapshot. Try a clearer photo, "
                        "or check that the LLM is reachable (API key, quota, model access)."
                    )
                else:
                    st.success(
                        f"Recorded: {txn['vendor_name'] or 'unknown vendor'} — ₹{txn['amount']}"
                    )
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
            with st.spinner("Thinking..."):
                try:
                    answer = llm.answer_question(question, context)
                except Exception:
                    st.error("⚠️ Couldn't get an answer.")
                    st.info(
                        "KAIROS couldn't reach the LLM for this question. Check that the "
                        "API key, quota, and model access are working."
                    )
                else:
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
