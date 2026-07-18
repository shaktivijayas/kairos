from kairos import llm, storage


def test_sms_webhook_creates_transaction_and_cash_limit_finding(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(
        llm,
        "classify_transaction",
        lambda text: {
            "classification": "business",
            "amount": 15000,
            "payment_mode": "cash",
            "vendor_name": "Sharma Traders",
        },
    )

    import webhook_app
    client = webhook_app.app.test_client()

    response = client.post("/sms", json={"text": "Paid Rs.15000 cash to Sharma Traders"})

    assert response.status_code == 200
    body = response.get_json()
    assert body["transaction"]["vendor_name"] == "Sharma Traders"
    assert len(body["findings"]) == 1
    assert body["findings"][0]["type"] == "cash_limit_breach"
    assert len(storage.load_transactions()) == 1


def test_sms_webhook_missing_text_returns_400(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))

    import webhook_app
    client = webhook_app.app.test_client()

    response = client.post("/sms", json={})

    assert response.status_code == 400
