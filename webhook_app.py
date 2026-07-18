import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

from kairos import config, llm, rules, storage

app = Flask(__name__)


def process_sms(text):
    parsed = llm.classify_transaction(text)
    txn = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "sms",
        "raw_text": text,
        "classification": parsed.get("classification"),
        "amount": parsed.get("amount"),
        "payment_mode": parsed.get("payment_mode"),
        "vendor_name": parsed.get("vendor_name"),
        "vendor_gstin": None,
        "invoice_number": None,
        "category_hint": None,
    }

    existing = storage.load_transactions()
    findings = []

    cash_finding = rules.check_cash_limit(existing, txn, config.CASH_LIMIT_INR)
    if cash_finding:
        findings.append(cash_finding)

    findings.extend(rules.find_deductions(txn))

    storage.append_transaction(txn)
    for f in findings:
        f["id"] = str(uuid.uuid4())
        f["timestamp"] = txn["timestamp"]
        f["transaction_id"] = txn["id"]
        storage.append_finding(f)

    return txn, findings


@app.route("/sms", methods=["POST"])
def sms_webhook():
    body = request.get_json(force=True) or {}
    text = body.get("text", "")
    if not text:
        return jsonify({"error": "missing 'text'"}), 400
    try:
        txn, findings = process_sms(text)
    except Exception:
        app.logger.exception("Failed to process SMS webhook payload")
        return jsonify({"error": "could not process this message"}), 502
    return jsonify({"transaction": txn, "findings": findings}), 200


if __name__ == "__main__":
    if config.NGROK_AUTHTOKEN:
        from pyngrok import ngrok

        ngrok.set_auth_token(config.NGROK_AUTHTOKEN)
        public_url = ngrok.connect(5000)
        print(f"ngrok tunnel: {public_url}")
    app.run(port=5000)
