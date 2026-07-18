from kairos import llm, storage


def test_process_scanned_document_flags_missing_gstin(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(
        llm,
        "read_document_image",
        lambda image_bytes: {
            "vendor_name": "Ganesh Stores",
            "vendor_gstin": None,
            "invoice_number": "INV-001",
            "amount": 2500,
            "category_hint": "stationery",
        },
    )

    import ui_app
    txn, findings = ui_app.process_scanned_document(b"fake-image-bytes")

    assert txn["vendor_name"] == "Ganesh Stores"
    assert txn["source"] == "camera"
    assert any(f["type"] == "vendor_risk" for f in findings)
    assert len(storage.load_transactions()) == 1
