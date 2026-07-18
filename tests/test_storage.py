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


def test_update_finding_modifies_matching_record(tmp_path):
    path = str(tmp_path / "findings.jsonl")
    storage.append_finding({"id": "f1", "acknowledged": False}, path=path)
    storage.append_finding({"id": "f2", "acknowledged": False}, path=path)

    result = storage.update_finding("f1", {"acknowledged": True}, path=path)

    assert result["acknowledged"] is True
    loaded = storage.load_findings(path=path)
    assert loaded[0]["acknowledged"] is True
    assert loaded[1]["acknowledged"] is False


def test_update_finding_returns_none_when_id_not_found(tmp_path):
    path = str(tmp_path / "findings.jsonl")
    storage.append_finding({"id": "f1"}, path=path)
    assert storage.update_finding("nonexistent", {"acknowledged": True}, path=path) is None
