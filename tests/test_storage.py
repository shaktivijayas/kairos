from kairos import storage


def test_append_and_load_transaction_roundtrip(tmp_path):
    path = str(tmp_path / "ledger.jsonl")
    txn = {"id": "t1", "amount": 100, "vendor_name": "Test Vendor"}

    storage.append_transaction(txn, path=path)
    loaded = storage.load_transactions(path=path)

    assert loaded == [txn]


def test_append_and_load_finding_roundtrip(tmp_path):
    path = str(tmp_path / "findings.jsonl")
    finding = {"id": "f1", "type": "cash_limit_breach"}

    storage.append_finding(finding, path=path)
    loaded = storage.load_findings(path=path)

    assert loaded == [finding]


def test_load_transactions_missing_file_returns_empty_list(tmp_path):
    path = str(tmp_path / "does_not_exist.jsonl")
    assert storage.load_transactions(path=path) == []


def test_default_path_is_used_when_monkeypatched(tmp_path, monkeypatch):
    patched_path = str(tmp_path / "ledger.jsonl")
    monkeypatch.setattr(storage, "LEDGER_PATH", patched_path)

    storage.append_transaction({"id": "t2"})
    loaded = storage.load_transactions()

    assert loaded == [{"id": "t2"}]
