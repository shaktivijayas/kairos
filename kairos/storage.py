import json
import os

LEDGER_PATH = os.path.join("data", "ledger.jsonl")
FINDINGS_PATH = os.path.join("data", "findings.jsonl")


def _append(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _load(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_transaction(txn, path=None):
    _append(path or LEDGER_PATH, txn)


def load_transactions(path=None):
    return _load(path or LEDGER_PATH)


def append_finding(finding, path=None):
    _append(path or FINDINGS_PATH, finding)


def load_findings(path=None):
    return _load(path or FINDINGS_PATH)
