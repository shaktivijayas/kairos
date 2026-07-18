from kairos import llm, profile, storage


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


def test_sms_webhook_llm_failure_returns_clean_502_not_a_traceback(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))

    def _boom(text):
        raise RuntimeError("simulated LLM/API failure")

    monkeypatch.setattr(llm, "classify_transaction", _boom)

    import webhook_app
    client = webhook_app.app.test_client()

    response = client.post("/sms", json={"text": "Paid Rs.2500 to Ganesh Stores"})

    assert response.status_code == 502
    assert response.get_json() == {"error": "could not process this message"}
    assert storage.load_transactions() == []  # nothing partially written


def test_get_profile_returns_defaults_when_none_saved(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "PROFILE_PATH", str(tmp_path / "profile.json"))

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.get("/profile")

    assert response.status_code == 200
    assert response.get_json()["tax_scheme"] == "regular"


def test_post_profile_saves_and_returns_updated_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(profile, "PROFILE_PATH", str(tmp_path / "profile.json"))

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.post("/profile", json={
        "legal_business_name": "Sharma Traders Pvt Ltd",
        "tax_scheme": "composition",
    })

    assert response.status_code == 200
    body = response.get_json()
    assert body["legal_business_name"] == "Sharma Traders Pvt Ltd"
    assert body["tax_scheme"] == "composition"

    get_response = client.get("/profile")
    assert get_response.get_json()["tax_scheme"] == "composition"
