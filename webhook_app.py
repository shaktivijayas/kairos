import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS

from kairos import config, itr_export, llm, profile, rules, storage

app = Flask(__name__)
# Permissive for now — the Lovable frontend's origin isn't known until that
# project exists. Tighten to specific origins once it's deployed.
CORS(app)


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
        f["acknowledged"] = False
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


def process_scan(image_bytes, mime_type="image/jpeg"):
    parsed = llm.read_document_image(image_bytes, mime_type=mime_type)
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
        f["acknowledged"] = False
        storage.append_finding(f)

    return txn, findings


@app.route("/scan", methods=["POST"])
def scan_document():
    if "file" not in request.files:
        return jsonify({"error": "missing 'file'"}), 400
    file = request.files["file"]
    image_bytes = file.read()
    mime_type = file.mimetype or "image/jpeg"
    try:
        txn, findings = process_scan(image_bytes, mime_type)
    except Exception:
        app.logger.exception("Failed to process scan upload")
        return jsonify({"error": "could not process this document"}), 502
    return jsonify({"transaction": txn, "findings": findings}), 200


@app.route("/profile", methods=["GET"])
def get_profile():
    return jsonify(profile.load_profile()), 200


@app.route("/profile", methods=["POST"])
def update_profile():
    body = request.get_json(force=True) or {}
    current = profile.load_profile()
    for key in ("legal_business_name", "trade_style", "business_category", "tax_scheme"):
        if key in body:
            current[key] = body[key]
    profile.save_profile(current)
    return jsonify(current), 200


@app.route("/transactions", methods=["GET"])
def get_transactions():
    source = request.args.get("source")
    transactions = storage.load_transactions()
    if source:
        transactions = [t for t in transactions if t.get("source") == source]
    return jsonify(transactions), 200


@app.route("/findings", methods=["GET"])
def get_findings():
    return jsonify(storage.load_findings()), 200


@app.route("/findings/<finding_id>", methods=["PATCH"])
def patch_finding(finding_id):
    body = request.get_json(force=True) or {}
    if "acknowledged" not in body:
        return jsonify({"error": "missing 'acknowledged'"}), 400
    updated = storage.update_finding(finding_id, {"acknowledged": bool(body["acknowledged"])})
    if updated is None:
        return jsonify({"error": "finding not found"}), 404
    return jsonify(updated), 200


@app.route("/itr/export", methods=["GET"])
def get_itr_export():
    transactions = storage.load_transactions()
    findings = storage.load_findings()
    return jsonify(itr_export.export_itr_json(transactions, findings)), 200


@app.route("/findings/<finding_id>/advice", methods=["POST"])
def finding_advice(finding_id):
    findings = storage.load_findings()
    finding = next((f for f in findings if f.get("id") == finding_id), None)
    if finding is None:
        return jsonify({"error": "finding not found"}), 404

    body = request.get_json(silent=True) or {}
    question = body.get("question") or f"What should I do about this: {finding['message']}"

    try:
        answer = llm.answer_question(question, {"finding": finding})
    except Exception:
        app.logger.exception("Failed to get advice for finding %s", finding_id)
        return jsonify({"error": "could not get advice"}), 502

    return jsonify({"answer": answer}), 200


if __name__ == "__main__":
    if config.NGROK_AUTHTOKEN:
        from pyngrok import ngrok

        ngrok.set_auth_token(config.NGROK_AUTHTOKEN)
        public_url = ngrok.connect(5000)
        print(f"ngrok tunnel: {public_url}")
    app.run(port=5000)
