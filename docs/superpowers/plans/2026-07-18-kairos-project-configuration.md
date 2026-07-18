# KAIROS Project Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the full KAIROS project — config, shared `kairos/` package (LLM wrapper, rules engine, storage, ITR export), the Flask SMS webhook, the Streamlit UI, and the `run.sh` launcher — from the current empty repo scaffold to a runnable local demo.

**Architecture:** Two local Python processes (`webhook_app.py` Flask, `ui_app.py` Streamlit) share one internal package (`kairos/`) so the SMS-ingestion path and the camera-scan path both funnel through the same classify → check-rules → store pipeline instead of duplicating logic.

**Tech Stack:** Python 3.11+, Flask, Streamlit, `google-genai` SDK calling Gemma 3 (`gemma-3-27b-it`) via the Google AI Studio API, `pyngrok`, `python-dotenv`, `pandas`, `pytest`. Storage is JSON Lines files on disk — no database.

## Global Constraints

- Cash-limit check defaults to ₹10,000/day (`CASH_LIMIT_INR`, overridable via `.env`), per Section 40A(3) — spec §Purpose.
- LLM calls use Gemma 3 (`gemma-3-27b-it`) exclusively — no fallback/switch to another model — spec §Components.
- Storage is JSON Lines on disk (`data/ledger.jsonl`, `data/findings.jsonl`) — no SQLite/database — spec §Out of Scope.
- `.env` (real secrets) stays gitignored; only `.env.example` is committed — spec §Configuration Files.
- All CA-facing outputs (chat answers, deduction findings) must read as "worth reviewing with your CA," never as confident tax advice — spec §Purpose.
- `rules.py` and `itr_export.py` must have zero LLM/network calls — they are the automated-test surface; `llm.py`, the Flask/Streamlit entry points' live-API behavior, and the camera flow are validated manually, not by automated tests — spec §Testing.

---

### Task 1: Project scaffolding and config files

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Modify: `.gitignore` (append Python + runtime-data entries to the existing file)
- Create: `data/.gitkeep`
- Create: `kairos/__init__.py` (empty)
- Create: `pytest.ini`
- Modify: `README.md`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: an importable `kairos` package, a working `pip install -r requirements.txt`, and `pytest` able to resolve `from kairos import ...` and `import webhook_app` / `import ui_app` from any test file, via `pythonpath = .` in `pytest.ini`.

- [ ] **Step 1: Create `requirements.txt`**

```
flask==3.0.3
streamlit==1.38.0
google-genai==0.3.0
python-dotenv==1.0.1
pandas==2.2.2
pyngrok==7.2.0
pytest==8.3.2
```

- [ ] **Step 2: Create `.env.example`**

```
GEMINI_API_KEY=
NGROK_AUTHTOKEN=
CASH_LIMIT_INR=10000
```

- [ ] **Step 3: Append Python and runtime-data entries to `.gitignore`**

Append to the end of the existing `.gitignore`:

```

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# KAIROS runtime data
data/*.jsonl
```

- [ ] **Step 4: Create `data/.gitkeep`**

Empty file at `data/.gitkeep` so the directory exists in git while `*.jsonl` contents stay ignored.

- [ ] **Step 5: Create `kairos/__init__.py`**

Empty file — marks `kairos/` as a package.

- [ ] **Step 6: Create `pytest.ini`**

```ini
[pytest]
pythonpath = .
```

- [ ] **Step 7: Replace `README.md` contents**

```markdown
# KAIROS

An ambient, ERP-free compliance shield for India's micro-merchants, freelancers, and gig workers. KAIROS reads forwarded banking SMS alerts and photographed invoices — no ERP integration, no GSTN portal login — and flags Section 40A(3) cash-limit breaches, vendor ITC risk, and unclaimed deductions (80C/80D/24b), with reasoning shown for every flag. It also answers "is this okay?" compliance questions before you act.

All outputs are framed as worth reviewing with your CA, not confident tax advice.

## Architecture

- `webhook_app.py` (Flask) — receives forwarded SMS via an ngrok tunnel
- `ui_app.py` (Streamlit) — camera scan, chat, and dashboard
- `kairos/` — shared logic: `llm.py` (Gemma 3), `rules.py` (statutory checks), `storage.py` (JSON Lines ledger), `itr_export.py` (ITR-1/ITR-4 JSON mapping)

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` (Google AI Studio) and `NGROK_AUTHTOKEN` (ngrok.com)
3. `./run.sh`

This starts the SMS webhook (its ngrok tunnel URL is printed to the console) and the Streamlit UI. Point an Android SMS-forwarder app at the printed ngrok URL + `/sms`.
```

- [ ] **Step 8: Install dependencies and verify imports resolve**

Run: `pip install -r requirements.txt`

Run: `python -c "import flask, streamlit, google.genai, dotenv, pandas, pyngrok, pytest"`
Expected: no output, exit code 0.

- [ ] **Step 9: Commit**

```bash
git add requirements.txt .env.example .gitignore data/.gitkeep kairos/__init__.py pytest.ini README.md
git commit -m "chore: scaffold project config, deps, and package layout"
```

---

### Task 2: `kairos/config.py`

**Files:**
- Create: `kairos/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: `.env` file (via `python-dotenv`).
- Produces: `config.GEMINI_API_KEY: str`, `config.NGROK_AUTHTOKEN: str`, `config.CASH_LIMIT_INR: int`, `config.GEMMA_MODEL: str` (constant `"gemma-3-27b-it"`).

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
import importlib


def test_default_cash_limit(monkeypatch):
    monkeypatch.delenv("CASH_LIMIT_INR", raising=False)
    from kairos import config
    importlib.reload(config)
    assert config.CASH_LIMIT_INR == 10000


def test_cash_limit_from_env(monkeypatch):
    monkeypatch.setenv("CASH_LIMIT_INR", "5000")
    from kairos import config
    importlib.reload(config)
    assert config.CASH_LIMIT_INR == 5000


def test_gemma_model_is_fixed():
    from kairos import config
    assert config.GEMMA_MODEL == "gemma-3-27b-it"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kairos.config'`

- [ ] **Step 3: Write `kairos/config.py`**

```python
import os

from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN", "")
CASH_LIMIT_INR = int(os.environ.get("CASH_LIMIT_INR", "10000"))
GEMMA_MODEL = "gemma-3-27b-it"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add kairos/config.py tests/test_config.py
git commit -m "feat: add config module for env vars and Gemma model constant"
```

---

### Task 3: `kairos/storage.py`

**Files:**
- Create: `kairos/storage.py`
- Test: `tests/test_storage.py`

**Interfaces:**
- Consumes: nothing (writes plain dicts to disk).
- Produces: `storage.LEDGER_PATH: str`, `storage.FINDINGS_PATH: str`, `storage.append_transaction(txn: dict, path: str | None = None) -> None`, `storage.load_transactions(path: str | None = None) -> list[dict]`, `storage.append_finding(finding: dict, path: str | None = None) -> None`, `storage.load_findings(path: str | None = None) -> list[dict]`.
  Note: each function resolves `path or LEDGER_PATH` (or `FINDINGS_PATH`) **inside the function body**, not as a bound default argument — this is what lets tests monkeypatch `storage.LEDGER_PATH` and have callers that omit `path` pick up the patched value.

- [ ] **Step 1: Write the failing tests**

`tests/test_storage.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kairos.storage'`

- [ ] **Step 3: Write `kairos/storage.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_storage.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add kairos/storage.py tests/test_storage.py
git commit -m "feat: add JSON Lines storage for ledger and findings"
```

---

### Task 4: `kairos/rules.py` — cash limit check (Section 40A(3))

**Files:**
- Create: `kairos/rules.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Consumes: nothing beyond plain dicts (no imports from `config`, `storage`, or `llm` — kept LLM/network-free per Global Constraints).
- Produces: `rules.check_cash_limit(transactions: list[dict], new_txn: dict, limit: int) -> dict | None`. Returned finding shape: `{"type": "cash_limit_breach", "severity": "red", "amount": float, "message": str, "reasons": list[str]}`.
  Transaction dict shape assumed throughout `rules.py`: `{"amount": float, "classification": "business"|"personal", "payment_mode": "cash"|"upi"|"card"|"unknown", "vendor_name": str|None, "vendor_gstin": str|None, "invoice_number": str|None, "raw_text": str, "category_hint": str|None, "timestamp": str (ISO8601)}`.

- [ ] **Step 1: Write the failing tests**

`tests/test_rules.py`:
```python
from kairos import rules


def _txn(**overrides):
    base = {
        "amount": 5000,
        "classification": "business",
        "payment_mode": "cash",
        "vendor_name": "Sharma Traders",
        "vendor_gstin": None,
        "invoice_number": None,
        "raw_text": "",
        "category_hint": None,
        "timestamp": "2026-07-18T10:00:00+00:00",
    }
    base.update(overrides)
    return base


def test_cash_limit_breach_when_same_day_same_vendor_total_exceeds_limit():
    existing = [_txn(amount=6000)]
    new_txn = _txn(amount=5000)

    finding = rules.check_cash_limit(existing, new_txn, limit=10000)

    assert finding is not None
    assert finding["type"] == "cash_limit_breach"
    assert finding["severity"] == "red"
    assert finding["amount"] == 1000  # 11000 total - 10000 limit
    assert "Sharma Traders" in finding["message"]
    assert len(finding["reasons"]) == 2


def test_no_breach_when_under_limit():
    existing = [_txn(amount=2000)]
    new_txn = _txn(amount=3000)

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_no_breach_for_non_cash_payment():
    existing = [_txn(amount=8000)]
    new_txn = _txn(amount=5000, payment_mode="upi")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_no_breach_for_personal_classification():
    existing = [_txn(amount=8000, classification="personal")]
    new_txn = _txn(amount=5000, classification="personal")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_different_vendors_do_not_combine():
    existing = [_txn(amount=8000, vendor_name="Other Vendor")]
    new_txn = _txn(amount=5000, vendor_name="Sharma Traders")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None


def test_different_day_does_not_combine():
    existing = [_txn(amount=8000, timestamp="2026-07-17T10:00:00+00:00")]
    new_txn = _txn(amount=5000, timestamp="2026-07-18T10:00:00+00:00")

    assert rules.check_cash_limit(existing, new_txn, limit=10000) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kairos.rules'`

- [ ] **Step 3: Write `kairos/rules.py` (cash limit portion only)**

```python
def check_cash_limit(transactions, new_txn, limit):
    if new_txn.get("payment_mode") != "cash" or new_txn.get("classification") != "business":
        return None

    vendor = new_txn.get("vendor_name")
    date = new_txn["timestamp"][:10]
    total = new_txn["amount"]

    for t in transactions:
        if (
            t.get("payment_mode") == "cash"
            and t.get("classification") == "business"
            and t.get("vendor_name") == vendor
            and t.get("timestamp", "")[:10] == date
        ):
            total += t["amount"]

    if total > limit:
        return {
            "type": "cash_limit_breach",
            "severity": "red",
            "amount": total - limit,
            "message": (
                f"Cash payments to {vendor or 'this vendor'} on {date} total "
                f"₹{total:.2f}, over the ₹{limit} daily limit under Section 40A(3)."
            ),
            "reasons": [
                f"₹{total:.2f} paid in cash to {vendor or 'unknown vendor'} on {date}",
                f"Section 40A(3) disallows cash business expenditure over ₹{limit}/day to a single person",
            ],
        }
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add kairos/rules.py tests/test_rules.py
git commit -m "feat: add Section 40A(3) cash-limit check to rules engine"
```

---

### Task 5: `kairos/rules.py` — vendor ITC risk scoring

**Files:**
- Modify: `kairos/rules.py`
- Modify: `tests/test_rules.py`

**Interfaces:**
- Consumes: same transaction dict shape as Task 4.
- Produces: `rules.score_vendor_risk(transactions: list[dict], new_txn: dict) -> dict | None`. Returned finding shape: `{"type": "vendor_risk", "severity": "yellow"|"red", "amount": None, "message": str, "reasons": list[str]}` (severity is `"red"` when 2+ reasons fire, else `"yellow"`; returns `None` when no reasons fire).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rules.py`:
```python
def test_vendor_risk_flags_missing_gstin():
    finding = rules.score_vendor_risk([], _txn(vendor_gstin=None))

    assert finding is not None
    assert finding["type"] == "vendor_risk"
    assert finding["severity"] == "yellow"
    assert "No GSTIN captured" in finding["reasons"][0]


def test_vendor_risk_flags_malformed_gstin():
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="NOT-A-GSTIN"))

    assert finding is not None
    assert any("does not match" in r for r in finding["reasons"])


def test_vendor_risk_passes_valid_gstin_with_no_history():
    finding = rules.score_vendor_risk([], _txn(vendor_gstin="27AAAAA0000A1Z5"))

    assert finding is None


def test_vendor_risk_flags_duplicate_invoice_number():
    existing = [_txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-100")]
    new_txn = _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-100")

    finding = rules.score_vendor_risk(existing, new_txn)

    assert finding is not None
    assert any("already seen" in r for r in finding["reasons"])


def test_vendor_risk_flags_amount_deviation_and_escalates_severity():
    existing = [
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-1", amount=1000),
        _txn(vendor_gstin="27AAAAA0000A1Z5", invoice_number="INV-2", amount=1100),
    ]
    new_txn = _txn(vendor_gstin=None, invoice_number="INV-3", amount=50000)

    finding = rules.score_vendor_risk(existing, new_txn)

    assert finding is not None
    assert finding["severity"] == "red"  # missing GSTIN + amount deviation = 2 reasons
    assert any("deviates sharply" in r for r in finding["reasons"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL with `AttributeError: module 'kairos.rules' has no attribute 'score_vendor_risk'`

- [ ] **Step 3: Add vendor risk scoring to `kairos/rules.py`**

Add to the top of the file and after `check_cash_limit`:
```python
import re

GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z]\d[Z][0-9A-Z]$")


def score_vendor_risk(transactions, new_txn):
    reasons = []
    gstin = new_txn.get("vendor_gstin")
    if not gstin:
        reasons.append("No GSTIN captured on this invoice")
    elif not GSTIN_PATTERN.match(gstin):
        reasons.append(f"GSTIN '{gstin}' does not match the standard 15-character format")

    invoice_number = new_txn.get("invoice_number")
    vendor = new_txn.get("vendor_name")
    if invoice_number and vendor:
        for t in transactions:
            if t.get("vendor_name") == vendor and t.get("invoice_number") == invoice_number:
                reasons.append(f"Invoice number '{invoice_number}' already seen for vendor '{vendor}'")
                break

    if vendor:
        prior_amounts = [
            t["amount"] for t in transactions
            if t.get("vendor_name") == vendor and t.get("amount") is not None
        ]
        if len(prior_amounts) >= 2:
            mean = sum(prior_amounts) / len(prior_amounts)
            variance = sum((a - mean) ** 2 for a in prior_amounts) / len(prior_amounts)
            stdev = variance ** 0.5
            amount = new_txn.get("amount")
            if stdev > 0 and amount is not None and abs(amount - mean) > 2 * stdev:
                reasons.append(
                    f"Amount ₹{amount:.2f} deviates sharply from this vendor's usual ₹{mean:.2f}"
                )

    if not reasons:
        return None

    severity = "red" if len(reasons) >= 2 else "yellow"
    return {
        "type": "vendor_risk",
        "severity": severity,
        "amount": None,
        "message": f"Vendor '{vendor or 'unknown'}' flagged as {severity} risk for ITC purposes.",
        "reasons": reasons,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules.py -v`
Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
git add kairos/rules.py tests/test_rules.py
git commit -m "feat: add vendor ITC risk scoring to rules engine"
```

---

### Task 6: `kairos/rules.py` — deduction opportunity finder

**Files:**
- Modify: `kairos/rules.py`
- Modify: `tests/test_rules.py`

**Interfaces:**
- Consumes: same transaction dict shape as Task 4.
- Produces: `rules.find_deductions(new_txn: dict) -> dict | None`. Returned finding shape: `{"type": "deduction_opportunity", "severity": "green", "amount": float|None, "message": str, "reasons": list[str]}`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_rules.py`:
```python
def test_find_deductions_matches_80c_keyword():
    finding = rules.find_deductions(_txn(raw_text="LIC premium payment", amount=12000))

    assert finding is not None
    assert finding["type"] == "deduction_opportunity"
    assert "80C" in finding["message"]
    assert finding["amount"] == 12000


def test_find_deductions_matches_80d_keyword():
    finding = rules.find_deductions(_txn(category_hint="health insurance renewal"))

    assert finding is not None
    assert "80D" in finding["message"]


def test_find_deductions_matches_24b_keyword():
    finding = rules.find_deductions(_txn(raw_text="Home loan EMI debited"))

    assert finding is not None
    assert "24b" in finding["message"]


def test_find_deductions_returns_none_when_no_keyword_matches():
    assert rules.find_deductions(_txn(raw_text="Paid for office chairs")) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rules.py -v`
Expected: FAIL with `AttributeError: module 'kairos.rules' has no attribute 'find_deductions'`

- [ ] **Step 3: Add deduction finder to `kairos/rules.py`**

Add to the end of the file:
```python
DEDUCTION_KEYWORDS = {
    "80C": ["lic", "life insurance", "ppf", "elss", "mutual fund", "tuition fee"],
    "80D": ["health insurance", "mediclaim", "medical insurance"],
    "24b": ["home loan", "housing loan", "emi"],
}


def find_deductions(new_txn):
    text = f"{new_txn.get('raw_text', '')} {new_txn.get('category_hint', '')}".lower()
    for section, keywords in DEDUCTION_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return {
                    "type": "deduction_opportunity",
                    "severity": "green",
                    "amount": new_txn.get("amount"),
                    "message": (
                        f"This looks like it may qualify for a Section {section} deduction "
                        "— worth reviewing with your CA."
                    ),
                    "reasons": [f"Matched keyword '{kw}' under Section {section}"],
                }
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rules.py -v`
Expected: 15 passed

- [ ] **Step 5: Commit**

```bash
git add kairos/rules.py tests/test_rules.py
git commit -m "feat: add deduction-opportunity finder to rules engine"
```

---

### Task 7: `kairos/itr_export.py`

**Files:**
- Create: `kairos/itr_export.py`
- Test: `tests/test_itr_export.py`

**Interfaces:**
- Consumes: `transactions: list[dict]` (shape from Task 4), `findings: list[dict]` (shapes from Tasks 4-6, each carrying `"type"`, `"amount"`, `"message"`).
- Produces: `itr_export.export_itr_json(transactions: list[dict], findings: list[dict]) -> dict` with keys `gross_business_receipts: float`, `total_business_expenses: float`, `section_40A3_disallowed: float`, `deductions_found: dict[str, float]` (keys `"80C"`, `"80D"`, `"24b"`), `vendor_risk_flags: int`, `for_review_with_ca: bool` (always `True`).

- [ ] **Step 1: Write the failing tests**

`tests/test_itr_export.py`:
```python
from kairos import itr_export


def test_export_aggregates_business_totals_and_disallowed_cash():
    transactions = [
        {"classification": "business", "amount": 20000},
        {"classification": "business", "amount": 5000},
        {"classification": "personal", "amount": 999},
    ]
    findings = [
        {"type": "cash_limit_breach", "amount": 1000, "message": "..."},
    ]

    result = itr_export.export_itr_json(transactions, findings)

    assert result["gross_business_receipts"] == 25000
    assert result["total_business_expenses"] == 25000
    assert result["section_40A3_disallowed"] == 1000
    assert result["for_review_with_ca"] is True


def test_export_sums_deductions_by_section():
    transactions = []
    findings = [
        {"type": "deduction_opportunity", "amount": 12000, "message": "Section 80C deduction — worth reviewing"},
        {"type": "deduction_opportunity", "amount": 3000, "message": "Section 80D deduction — worth reviewing"},
        {"type": "deduction_opportunity", "amount": 8000, "message": "Section 80C deduction — worth reviewing"},
    ]

    result = itr_export.export_itr_json(transactions, findings)

    assert result["deductions_found"] == {"80C": 20000, "80D": 3000, "24b": 0}


def test_export_counts_vendor_risk_flags():
    findings = [
        {"type": "vendor_risk", "amount": None, "message": "..."},
        {"type": "vendor_risk", "amount": None, "message": "..."},
        {"type": "cash_limit_breach", "amount": 500, "message": "..."},
    ]

    result = itr_export.export_itr_json([], findings)

    assert result["vendor_risk_flags"] == 2


def test_export_handles_no_transactions_or_findings():
    result = itr_export.export_itr_json([], [])

    assert result["gross_business_receipts"] == 0
    assert result["section_40A3_disallowed"] == 0
    assert result["deductions_found"] == {"80C": 0, "80D": 0, "24b": 0}
    assert result["vendor_risk_flags"] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_itr_export.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kairos.itr_export'`

- [ ] **Step 3: Write `kairos/itr_export.py`**

```python
def export_itr_json(transactions, findings):
    business_txns = [t for t in transactions if t.get("classification") == "business"]
    gross_receipts = sum(t["amount"] for t in business_txns if t.get("amount", 0) > 0)
    total_expenses = sum(t["amount"] for t in business_txns)

    disallowed_40a3 = sum(
        f["amount"] for f in findings
        if f["type"] == "cash_limit_breach" and f.get("amount")
    )

    deductions_by_section = {"80C": 0.0, "80D": 0.0, "24b": 0.0}
    for f in findings:
        if f["type"] == "deduction_opportunity" and f.get("amount"):
            for section in deductions_by_section:
                if f"Section {section}" in f["message"]:
                    deductions_by_section[section] += f["amount"]

    vendor_risk_count = sum(1 for f in findings if f["type"] == "vendor_risk")

    return {
        "gross_business_receipts": round(gross_receipts, 2),
        "total_business_expenses": round(total_expenses, 2),
        "section_40A3_disallowed": round(disallowed_40a3, 2),
        "deductions_found": {k: round(v, 2) for k, v in deductions_by_section.items()},
        "vendor_risk_flags": vendor_risk_count,
        "for_review_with_ca": True,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_itr_export.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add kairos/itr_export.py tests/test_itr_export.py
git commit -m "feat: add ITR-1/ITR-4 JSON export mapping"
```

---

### Task 8: `kairos/llm.py` — Gemma 3 wrapper

**Files:**
- Create: `kairos/llm.py`

**Interfaces:**
- Consumes: `config.GEMINI_API_KEY`, `config.GEMMA_MODEL` from Task 2.
- Produces: `llm.classify_transaction(text: str) -> dict` (keys: `classification`, `amount`, `payment_mode`, `vendor_name`), `llm.read_document_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict` (keys: `vendor_name`, `vendor_gstin`, `invoice_number`, `amount`, `category_hint`), `llm.answer_question(question: str, context: dict) -> str`.
  No automated tests per Global Constraints — this module makes live network calls to the Gemma 3 API. Verified manually in Step 2 below.

- [ ] **Step 1: Write `kairos/llm.py`**

```python
import json

from google import genai
from google.genai import types

from kairos import config

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


CLASSIFY_PROMPT = """You are a transaction classifier for an Indian small-business compliance tool.
Given a bank SMS alert, return a JSON object with these keys:
"classification" ("business" or "personal"), "amount" (number), "payment_mode" ("cash", "upi", "card", or "unknown"), "vendor_name" (string or null).
SMS: {text}"""


def classify_transaction(text):
    client = _get_client()
    response = client.models.generate_content(
        model=config.GEMMA_MODEL,
        contents=CLASSIFY_PROMPT.format(text=text),
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


DOCUMENT_PROMPT = """You are reading a photographed Indian business invoice or cash slip.
Return a JSON object with these keys:
"vendor_name" (string or null), "vendor_gstin" (string or null), "invoice_number" (string or null),
"amount" (number or null), "category_hint" (short string describing what was purchased, or null)."""


def read_document_image(image_bytes, mime_type="image/jpeg"):
    client = _get_client()
    response = client.models.generate_content(
        model=config.GEMMA_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            DOCUMENT_PROMPT,
        ],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return json.loads(response.text)


ANSWER_PROMPT = """You are KAIROS, a compliance assistant for an Indian micro-merchant. Answer plainly and briefly.
Always end with: "Worth reviewing with your CA before you act."
Context (recent transactions and flags): {context}
Question: {question}"""


def answer_question(question, context):
    client = _get_client()
    response = client.models.generate_content(
        model=config.GEMMA_MODEL,
        contents=ANSWER_PROMPT.format(context=json.dumps(context), question=question),
    )
    return response.text
```

- [ ] **Step 2: Manually verify against the live Gemma 3 API**

Prerequisite: `.env` has a real `GEMINI_API_KEY` (copy `.env.example` to `.env` and fill it in if not already done).

Run:
```bash
python -c "
from kairos import llm
result = llm.classify_transaction('Paid Rs.2500 to Ganesh Stores via UPI')
print(result)
assert set(result) >= {'classification', 'amount', 'payment_mode', 'vendor_name'}
print('OK')
"
```
Expected: prints a dict with those four keys, then `OK`. If it errors, check `GEMINI_API_KEY` is set and the `gemma-3-27b-it` model id is available to your API key's tier.

- [ ] **Step 3: Commit**

```bash
git add kairos/llm.py
git commit -m "feat: add Gemma 3 wrapper for classify/read-document/answer"
```

---

### Task 9: `webhook_app.py` — Flask SMS webhook

**Files:**
- Create: `webhook_app.py`
- Test: `tests/test_webhook_app.py`

**Interfaces:**
- Consumes: `config.CASH_LIMIT_INR`, `config.NGROK_AUTHTOKEN` (Task 2); `llm.classify_transaction` (Task 8); `rules.check_cash_limit`, `rules.find_deductions` (Tasks 4, 6); `storage.append_transaction`, `storage.append_finding`, `storage.load_transactions`, `storage.LEDGER_PATH`, `storage.FINDINGS_PATH` (Task 3).
- Produces: `webhook_app.app` (Flask instance), `webhook_app.process_sms(text: str) -> tuple[dict, list[dict]]`, HTTP route `POST /sms` accepting JSON `{"text": str}`, returning `{"transaction": dict, "findings": list[dict]}` with status 200, or `{"error": str}` with status 400 if `text` is missing.
  Test mocks `llm.classify_transaction` — this task tests routing/integration logic, not live Gemma output (per Global Constraints).

- [ ] **Step 1: Write the failing test**

`tests/test_webhook_app.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_webhook_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'webhook_app'`

- [ ] **Step 3: Write `webhook_app.py`**

```python
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

    deduction_finding = rules.find_deductions(txn)
    if deduction_finding:
        findings.append(deduction_finding)

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
    txn, findings = process_sms(text)
    return jsonify({"transaction": txn, "findings": findings}), 200


if __name__ == "__main__":
    if config.NGROK_AUTHTOKEN:
        from pyngrok import ngrok

        ngrok.set_auth_token(config.NGROK_AUTHTOKEN)
        public_url = ngrok.connect(5000)
        print(f"ngrok tunnel: {public_url}")
    app.run(port=5000)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_webhook_app.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add webhook_app.py tests/test_webhook_app.py
git commit -m "feat: add Flask SMS webhook wiring classify -> rules -> storage"
```

---

### Task 10: `ui_app.py` — Streamlit UI

**Files:**
- Create: `ui_app.py`
- Test: `tests/test_ui_app.py`

**Interfaces:**
- Consumes: `llm.read_document_image`, `llm.answer_question` (Task 8); `rules.score_vendor_risk`, `rules.find_deductions` (Tasks 5, 6); `storage.append_transaction`, `storage.append_finding`, `storage.load_transactions`, `storage.load_findings`, `storage.LEDGER_PATH`, `storage.FINDINGS_PATH` (Task 3); `itr_export.export_itr_json` (Task 7).
- Produces: `ui_app.process_scanned_document(image_bytes: bytes) -> tuple[dict, list[dict]]` (pure logic, testable), `ui_app.render()` (Streamlit rendering, not unit-tested — exercised manually in Step 5).
  The business logic is factored into `process_scanned_document` specifically so it's testable without a running Streamlit script context.

- [ ] **Step 1: Write the failing test**

`tests/test_ui_app.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ui_app.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ui_app'`

- [ ] **Step 3: Write `ui_app.py`**

```python
import uuid
from datetime import datetime, timezone

import streamlit as st

from kairos import itr_export, llm, rules, storage


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

    risk_finding = rules.score_vendor_risk(existing, txn)
    if risk_finding:
        findings.append(risk_finding)

    deduction_finding = rules.find_deductions(txn)
    if deduction_finding:
        findings.append(deduction_finding)

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
            txn, findings = process_scanned_document(photo.getvalue())
            st.success(f"Recorded: {txn['vendor_name'] or 'unknown vendor'} — ₹{txn['amount']}")
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
            answer = llm.answer_question(question, context)
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ui_app.py -v`
Expected: 1 passed

- [ ] **Step 5: Manually verify the Streamlit rendering**

Run: `streamlit run ui_app.py`
Expected: browser opens to three tabs (Scan Document, Ask KAIROS, Dashboard); the camera tab requests camera permission; Dashboard shows empty tables until a document is scanned or an SMS is posted to the webhook.

- [ ] **Step 6: Commit**

```bash
git add ui_app.py tests/test_ui_app.py
git commit -m "feat: add Streamlit UI for scan/ask/dashboard"
```

---

### Task 11: `run.sh` and end-to-end verification

**Files:**
- Create: `run.sh`

**Interfaces:**
- Consumes: `webhook_app.py` (Task 9), `ui_app.py` (Task 10).
- Produces: a single command (`./run.sh`) that starts both processes together and tears the webhook down cleanly on exit.

- [ ] **Step 1: Write `run.sh`**

```bash
#!/usr/bin/env bash
set -e

cleanup() {
  if [ -n "$WEBHOOK_PID" ]; then
    kill "$WEBHOOK_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

python webhook_app.py &
WEBHOOK_PID=$!

streamlit run ui_app.py
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x run.sh`

- [ ] **Step 3: Manually verify end-to-end**

Prerequisite: `.env` has real `GEMINI_API_KEY` and `NGROK_AUTHTOKEN`.

Run: `./run.sh`
Expected: console prints an `ngrok tunnel: ...` URL from the Flask process, then Streamlit opens in the browser.

In a second terminal, with the printed ngrok URL:
```bash
curl -X POST <ngrok-url>/sms -H "Content-Type: application/json" -d '{"text": "Paid Rs.12000 cash to Ramesh Kirana Store"}'
```
Expected: JSON response with a `transaction` and a `cash_limit_breach` finding (since ₹12,000 > the ₹10,000 default). Refresh the Streamlit Dashboard tab — the new transaction and finding appear in the tables.

Press `Ctrl+C` in the first terminal.
Expected: both the Streamlit process and the background Flask/ngrok process exit (no orphaned `python webhook_app.py` process left running — verify with `ps aux | grep webhook_app` showing nothing).

- [ ] **Step 4: Commit**

```bash
git add run.sh
git commit -m "feat: add run.sh to launch webhook and UI together"
```

---

## Self-Review Notes

- **Spec coverage:** Architecture (Task 1 scaffolding + Task 9/10 processes) ✓; `config.py` ✓ (Task 2); `llm.py` three functions ✓ (Task 8); `storage.py` ✓ (Task 3); `rules.py` all three checks ✓ (Tasks 4-6); `itr_export.py` ✓ (Task 7); all Configuration Files (`requirements.txt`, `.env.example`, `.gitignore`, `data/`, `README.md`, `run.sh`) ✓ (Tasks 1, 11); Testing scope (rules/storage/itr_export automated, llm/webhook-live/streamlit-rendering manual) ✓ matches spec's Testing section exactly, with the addition of mocked-llm routing tests for `webhook_app.py`/`ui_app.py` (does not violate the spec — the live LLM call itself is still never exercised by an automated test).
- **Placeholder scan:** no TBD/TODO; every step has complete, runnable code or an exact command with expected output.
- **Type consistency:** transaction dict shape is defined once (Task 4's docstring-equivalent Interfaces block) and reused verbatim by Tasks 5, 6, 7, 9, 10. Finding dict shape (`type`, `severity`, `amount`, `message`, `reasons`) is consistent across `check_cash_limit`, `score_vendor_risk`, `find_deductions`, and consumed identically by `itr_export.export_itr_json`, `webhook_app.process_sms`, and `ui_app.process_scanned_document`.
