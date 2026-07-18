import io

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


def test_get_transactions_returns_all(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    storage.append_transaction({"id": "t1", "source": "sms"})
    storage.append_transaction({"id": "t2", "source": "camera"})

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.get("/transactions")

    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_get_transactions_filters_by_source(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    storage.append_transaction({"id": "t1", "source": "sms"})
    storage.append_transaction({"id": "t2", "source": "camera"})

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.get("/transactions?source=sms")

    body = response.get_json()
    assert len(body) == 1
    assert body[0]["id"] == "t1"


def test_get_findings_returns_all(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    storage.append_finding({"id": "f1"})
    storage.append_finding({"id": "f2"})

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.get("/findings")

    assert response.status_code == 200
    assert len(response.get_json()) == 2


def test_scan_endpoint_flags_vendor_risk_for_regular_scheme(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(profile, "PROFILE_PATH", str(tmp_path / "profile.json"))
    monkeypatch.setattr(
        llm,
        "read_document_image",
        lambda image_bytes, mime_type="image/jpeg": {
            "vendor_name": "Ganesh Stores",
            "vendor_gstin": None,
            "invoice_number": "INV-001",
            "amount": 2500,
            "category_hint": "stationery",
        },
    )

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.post(
        "/scan",
        data={"file": (io.BytesIO(b"fake-image-bytes"), "invoice.jpg")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    body = response.get_json()
    assert any(f["type"] == "vendor_risk" for f in body["findings"])


def test_scan_endpoint_skips_vendor_risk_for_composition_scheme(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(profile, "PROFILE_PATH", str(tmp_path / "profile.json"))
    profile.save_profile({"tax_scheme": "composition"})
    monkeypatch.setattr(
        llm,
        "read_document_image",
        lambda image_bytes, mime_type="image/jpeg": {
            "vendor_name": "Ganesh Stores",
            "vendor_gstin": None,
            "invoice_number": "INV-001",
            "amount": 2500,
            "category_hint": "stationery",
        },
    )

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.post(
        "/scan",
        data={"file": (io.BytesIO(b"fake-image-bytes"), "invoice.jpg")},
        content_type="multipart/form-data",
    )

    body = response.get_json()
    assert not any(f["type"] == "vendor_risk" for f in body["findings"])


def test_scan_endpoint_missing_file_returns_400(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.post("/scan", data={}, content_type="multipart/form-data")

    assert response.status_code == 400


def test_get_itr_export_returns_aggregated_json(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    storage.append_transaction({"classification": "business", "amount": 5000})

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.get("/itr/export")

    assert response.status_code == 200
    body = response.get_json()
    assert body["gross_business_receipts"] == 5000
    assert body["for_review_with_ca"] is True


def test_patch_finding_acknowledges_it(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    storage.append_finding({"id": "f1", "acknowledged": False})

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.patch("/findings/f1", json={"acknowledged": True})

    assert response.status_code == 200
    assert response.get_json()["acknowledged"] is True


def test_patch_finding_404_when_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.patch("/findings/nope", json={"acknowledged": True})

    assert response.status_code == 404


def test_patch_finding_missing_field_returns_400(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    storage.append_finding({"id": "f1", "acknowledged": False})

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.patch("/findings/f1", json={})

    assert response.status_code == 400


def test_finding_advice_returns_llm_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    storage.append_finding({"id": "f1", "message": "Cash breach", "reasons": []})
    monkeypatch.setattr(llm, "answer_question", lambda q, ctx: "Pay by UPI instead.")

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.post("/findings/f1/advice", json={})

    assert response.status_code == 200
    assert response.get_json()["answer"] == "Pay by UPI instead."


def test_finding_advice_404_when_finding_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.post("/findings/nope/advice", json={})

    assert response.status_code == 404


def test_finding_advice_502_on_llm_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    storage.append_finding({"id": "f1", "message": "Cash breach", "reasons": []})

    def _boom(q, ctx):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm, "answer_question", _boom)

    import webhook_app
    client = webhook_app.app.test_client()
    response = client.post("/findings/f1/advice", json={})

    assert response.status_code == 502
