# KAIROS Lovable Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the backend API surface the new frontend needs (Phase A), then build the four-screen Lovable frontend against it (Phase B), replacing the Streamlit UI.

**Architecture:** Phase A adds REST routes to `webhook_app.py` (already deployed to Render) backed by the existing `kairos/` package, plus a new `kairos/profile.py` module for business metadata. Phase B is built by Lovable's own agent via MCP — not hand-written by us — following the Fintra-derived design system, calling the Phase A routes through Lovable's Supabase edge functions.

**Tech Stack:** Phase A: Python/Flask, pytest (TDD, same pattern as the existing `/sms` route). Phase B: Lovable (React/Tailwind/shadcn), driven via the `lovable` MCP tools.

## Global Constraints

- Single-business, no login — all storage stays one shared file, not per-user (spec §Auth).
- `tax_scheme` is either `"regular"` or `"composition"`; when `"composition"`, `score_vendor_risk` must be skipped (spec §Screens: Onboarding).
- Palette: background `#F2F0EA`, ink `#111111`, accent `#D7FF3F` (chartreuse, CTAs only, never a background fill) (spec §Visual Design System).
- Typography: Space Grotesk for headlines, Inter for body (spec §Visual Design System).
- Buttons: fully rounded (pill). Black fill/white text for primary actions; chartreuse fill/black text for the single top CTA per screen (spec §Visual Design System).
- Cards: light gray `#F5F5F2`, rounded, generous padding, icon + big bold number + small gray caption pattern (spec §Visual Design System).
- Red/yellow/green are semantic status colors used only in the Triage Flag Matrix — never compete with the chartreuse brand accent elsewhere (spec §Visual Design System).
- Render API base URL: `https://kairos-api-i8rt.onrender.com` (spec §Deployment).
- All new Flask routes must have Flask-test-client tests with `llm` calls mocked, following `tests/test_webhook_app.py`'s existing pattern (spec §Testing).

---

## Phase A: Backend API

### Task 1: `kairos/profile.py`

**Files:**
- Create: `kairos/profile.py`
- Test: `tests/test_profile.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `profile.PROFILE_PATH: str`, `profile.DEFAULT_PROFILE: dict` (keys: `legal_business_name`, `trade_style`, `business_category`, `tax_scheme` — default `tax_scheme` is `"regular"`), `profile.load_profile(path: str | None = None) -> dict`, `profile.save_profile(profile: dict, path: str | None = None) -> None`. Same `path or DEFAULT_PATH`-resolved-inside-the-function pattern as `kairos/storage.py`, so tests can monkeypatch `profile.PROFILE_PATH`.

- [ ] **Step 1: Write the failing tests**

`tests/test_profile.py`:
```python
from kairos import profile


def test_load_profile_returns_default_when_missing(tmp_path):
    path = str(tmp_path / "profile.json")
    result = profile.load_profile(path=path)
    assert result["tax_scheme"] == "regular"
    assert result["legal_business_name"] is None


def test_save_and_load_profile_roundtrip(tmp_path):
    path = str(tmp_path / "profile.json")
    data = {
        "legal_business_name": "Sharma Traders Pvt Ltd",
        "trade_style": "Sharma Traders",
        "business_category": "Retail",
        "tax_scheme": "composition",
    }
    profile.save_profile(data, path=path)
    assert profile.load_profile(path=path) == data


def test_save_profile_overwrites_existing(tmp_path):
    path = str(tmp_path / "profile.json")
    profile.save_profile({"tax_scheme": "regular"}, path=path)
    profile.save_profile({"tax_scheme": "composition"}, path=path)
    assert profile.load_profile(path=path)["tax_scheme"] == "composition"


def test_default_path_is_used_when_monkeypatched(tmp_path, monkeypatch):
    patched_path = str(tmp_path / "profile.json")
    monkeypatch.setattr(profile, "PROFILE_PATH", patched_path)
    profile.save_profile({"tax_scheme": "composition"})
    assert profile.load_profile()["tax_scheme"] == "composition"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_profile.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'kairos.profile'`

- [ ] **Step 3: Write `kairos/profile.py`**

```python
import json
import os

PROFILE_PATH = os.path.join("data", "profile.json")

DEFAULT_PROFILE = {
    "legal_business_name": None,
    "trade_style": None,
    "business_category": None,
    "tax_scheme": "regular",
}


def load_profile(path=None):
    p = path or PROFILE_PATH
    if not os.path.exists(p):
        return dict(DEFAULT_PROFILE)
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def save_profile(profile, path=None):
    p = path or PROFILE_PATH
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(profile, f)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_profile.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add kairos/profile.py tests/test_profile.py
git commit -m "feat: add profile module for business metadata and tax scheme"
```

---

### Task 2: `GET /profile`, `POST /profile`

**Files:**
- Modify: `webhook_app.py`
- Modify: `tests/test_webhook_app.py`

**Interfaces:**
- Consumes: `profile.load_profile`, `profile.save_profile` (Task 1).
- Produces: `GET /profile` → 200 with the profile dict. `POST /profile` → accepts a JSON body with any of `legal_business_name`, `trade_style`, `business_category`, `tax_scheme`, merges onto the existing profile (partial updates allowed), saves, returns 200 with the full updated profile dict.

- [ ] **Step 1: Write the failing tests**

Add to the top of `tests/test_webhook_app.py`:
```python
from kairos import llm, profile, storage
```
(replacing the existing `from kairos import llm, storage` line)

Append to `tests/test_webhook_app.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webhook_app.py -v`
Expected: FAIL with `AttributeError` (no `/profile` route registered — 404 on the test client, so the response won't have the expected JSON)

- [ ] **Step 3: Add the routes to `webhook_app.py`**

Change the import line:
```python
from kairos import config, llm, rules, storage
```
to:
```python
from kairos import config, llm, profile, rules, storage
```

Add these routes (anywhere before the `if __name__ == "__main__":` guard):
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_webhook_app.py -v`
Expected: all tests pass, including the 2 new ones

- [ ] **Step 5: Commit**

```bash
git add webhook_app.py tests/test_webhook_app.py
git commit -m "feat: add GET/POST /profile routes"
```

---

### Task 3: `GET /transactions`, `GET /findings`

**Files:**
- Modify: `webhook_app.py`
- Modify: `tests/test_webhook_app.py`

**Interfaces:**
- Consumes: `storage.load_transactions`, `storage.load_findings` (existing).
- Produces: `GET /transactions` → 200 with a JSON array of all transactions; accepts an optional `?source=sms|camera` query param that filters by the `source` field. `GET /findings` → 200 with a JSON array of all findings.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webhook_app.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webhook_app.py -v`
Expected: FAIL (routes don't exist yet, 404s)

- [ ] **Step 3: Add the routes to `webhook_app.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_webhook_app.py -v`
Expected: all tests pass, including the 3 new ones

- [ ] **Step 5: Commit**

```bash
git add webhook_app.py tests/test_webhook_app.py
git commit -m "feat: add GET /transactions (with source filter) and GET /findings"
```

---

### Task 4: `POST /scan`, and composition-scheme-aware vendor risk in both entry points

**Files:**
- Modify: `webhook_app.py`
- Modify: `ui_app.py`
- Modify: `tests/test_webhook_app.py`
- Modify: `tests/test_ui_app.py`

**Interfaces:**
- Consumes: `llm.read_document_image(image_bytes, mime_type)` (existing), `rules.score_vendor_risk`, `rules.find_deductions` (existing), `profile.load_profile` (Task 1).
- Produces: `webhook_app.process_scan(image_bytes: bytes, mime_type: str = "image/jpeg") -> tuple[dict, list[dict]]`, route `POST /scan` accepting `multipart/form-data` with a `file` field, returning `{"transaction": dict, "findings": list[dict]}` at 200, or `{"error": str}` at 400 (missing file) / 502 (processing failure). Both `webhook_app.process_scan` and `ui_app.process_scanned_document` now skip `rules.score_vendor_risk` when `profile.load_profile()["tax_scheme"] == "composition"`.

- [ ] **Step 1: Write the failing tests**

Add `import io` to the top of `tests/test_webhook_app.py`.

Append to `tests/test_webhook_app.py`:
```python
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
```

Append to `tests/test_ui_app.py`:
```python
def test_process_scanned_document_skips_vendor_risk_for_composition_scheme(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setattr(storage, "FINDINGS_PATH", str(tmp_path / "findings.jsonl"))
    monkeypatch.setattr(profile, "PROFILE_PATH", str(tmp_path / "profile.json"))
    profile.save_profile({"tax_scheme": "composition"})
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

    assert not any(f["type"] == "vendor_risk" for f in findings)
```
And add `profile` to that file's existing `from kairos import llm, storage` import line, making it `from kairos import llm, profile, storage`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webhook_app.py tests/test_ui_app.py -v`
Expected: FAIL — `/scan` doesn't exist (404s), and the existing `test_process_scanned_document_flags_missing_gstin` test still passes but the new composition test fails since the skip logic doesn't exist yet

- [ ] **Step 3: Add `process_scan` and the route to `webhook_app.py`**

Add to the import line, making it:
```python
from kairos import config, llm, profile, rules, storage
```

Add this function and route (anywhere before the `if __name__ == "__main__":` guard):
```python
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
```

- [ ] **Step 4: Add the same composition-scheme skip to `ui_app.py`**

Change the import line:
```python
from kairos import itr_export, llm, rules, storage
```
to:
```python
from kairos import itr_export, llm, profile, rules, storage
```

Change this block in `process_scanned_document`:
```python
    risk_finding = rules.score_vendor_risk(existing, txn)
    if risk_finding:
        findings.append(risk_finding)
```
to:
```python
    if profile.load_profile().get("tax_scheme") != "composition":
        risk_finding = rules.score_vendor_risk(existing, txn)
        if risk_finding:
            findings.append(risk_finding)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_webhook_app.py tests/test_ui_app.py -v`
Expected: all tests pass, including the 4 new ones

- [ ] **Step 6: Commit**

```bash
git add webhook_app.py ui_app.py tests/test_webhook_app.py tests/test_ui_app.py
git commit -m "feat: add POST /scan and skip vendor risk for composition scheme"
```

---

### Task 5: `GET /itr/export`

**Files:**
- Modify: `webhook_app.py`
- Modify: `tests/test_webhook_app.py`

**Interfaces:**
- Consumes: `itr_export.export_itr_json(transactions, findings)` (existing).
- Produces: `GET /itr/export` → 200 with the ITR export JSON.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_webhook_app.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_webhook_app.py -v`
Expected: FAIL (route doesn't exist, 404)

- [ ] **Step 3: Add the route to `webhook_app.py`**

Add to the import line, making it:
```python
from kairos import config, itr_export, llm, profile, rules, storage
```

Add this route:
```python
@app.route("/itr/export", methods=["GET"])
def get_itr_export():
    transactions = storage.load_transactions()
    findings = storage.load_findings()
    return jsonify(itr_export.export_itr_json(transactions, findings)), 200
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_webhook_app.py -v`
Expected: all tests pass, including the new one

- [ ] **Step 5: Commit**

```bash
git add webhook_app.py tests/test_webhook_app.py
git commit -m "feat: add GET /itr/export"
```

---

### Task 6: `storage.update_finding` and `PATCH /findings/<id>`

**Files:**
- Modify: `kairos/storage.py`
- Modify: `webhook_app.py`
- Modify: `tests/test_storage.py`
- Modify: `tests/test_webhook_app.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `storage.update_finding(finding_id: str, updates: dict, path: str | None = None) -> dict | None` (returns the updated record, or `None` if no finding with that id exists). Route `PATCH /findings/<finding_id>` accepting `{"acknowledged": bool}`, returning the updated finding at 200, `{"error": ...}` at 400 (missing `acknowledged`) or 404 (not found). Findings created by `process_sms` (existing) and `process_scan` (Task 4) now include `"acknowledged": False` at creation time.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_storage.py`:
```python
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
```

Append to `tests/test_webhook_app.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_storage.py tests/test_webhook_app.py -v`
Expected: FAIL — `storage.update_finding` doesn't exist (`AttributeError`), and `/findings/<id>` route doesn't exist (404)

- [ ] **Step 3: Add `update_finding` to `kairos/storage.py`**

Add to the end of the file:
```python
def update_finding(finding_id, updates, path=None):
    p = path or FINDINGS_PATH
    findings = _load(p)
    updated = None
    for f in findings:
        if f.get("id") == finding_id:
            f.update(updates)
            updated = f
            break
    if updated is None:
        return None
    with open(p, "w", encoding="utf-8") as fh:
        for f in findings:
            fh.write(json.dumps(f) + "\n")
    return updated
```

- [ ] **Step 4: Add the route to `webhook_app.py`, and mark findings acknowledged=False at creation**

Add this route:
```python
@app.route("/findings/<finding_id>", methods=["PATCH"])
def patch_finding(finding_id):
    body = request.get_json(force=True) or {}
    if "acknowledged" not in body:
        return jsonify({"error": "missing 'acknowledged'"}), 400
    updated = storage.update_finding(finding_id, {"acknowledged": bool(body["acknowledged"])})
    if updated is None:
        return jsonify({"error": "finding not found"}), 404
    return jsonify(updated), 200
```

In `process_sms`, change:
```python
    for f in findings:
        f["id"] = str(uuid.uuid4())
        f["timestamp"] = txn["timestamp"]
        f["transaction_id"] = txn["id"]
        storage.append_finding(f)
```
to:
```python
    for f in findings:
        f["id"] = str(uuid.uuid4())
        f["timestamp"] = txn["timestamp"]
        f["transaction_id"] = txn["id"]
        f["acknowledged"] = False
        storage.append_finding(f)
```

Make the identical change in `process_scan` (added in Task 4) — its finding-tagging loop has the same shape.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_storage.py tests/test_webhook_app.py -v`
Expected: all tests pass, including the 5 new ones

- [ ] **Step 6: Commit**

```bash
git add kairos/storage.py webhook_app.py tests/test_storage.py tests/test_webhook_app.py
git commit -m "feat: add PATCH /findings/<id> to acknowledge findings"
```

---

### Task 7: `POST /findings/<id>/advice`

**Files:**
- Modify: `webhook_app.py`
- Modify: `tests/test_webhook_app.py`

**Interfaces:**
- Consumes: `llm.answer_question(question, context)` (existing).
- Produces: route `POST /findings/<finding_id>/advice`, optional JSON body `{"question": str}` (defaults to a generic prompt referencing the finding's message), returns `{"answer": str}` at 200, `{"error": ...}` at 404 (finding not found) or 502 (LLM failure).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_webhook_app.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_webhook_app.py -v`
Expected: FAIL (route doesn't exist, 404 on all three)

- [ ] **Step 3: Add the route to `webhook_app.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_webhook_app.py -v`
Expected: all tests pass, including the 3 new ones

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all tests pass (this is the last Phase A task — confirm nothing regressed across the whole backend)

- [ ] **Step 6: Commit and push**

```bash
git add webhook_app.py tests/test_webhook_app.py
git commit -m "feat: add POST /findings/<id>/advice"
git push origin main
```

Render auto-redeploys from `main` — Phase B can now build against the live API.

---

## Phase B: Lovable Frontend

Each task here is an MCP message to Lovable's own agent, not hand-written code. Verify each with `get_diff` (review what Lovable changed) and `render_project_widget` (see it live), not pytest.

### Task 8: Create the Lovable project, establish the design system, build Onboarding & Profile Setup

- [ ] **Step 1: Resolve the workspace**

Call `list_workspaces`. If there's exactly one, use its id. If there are several, ask the user which to use before proceeding.

- [ ] **Step 2: Create the project**

Call `create_project` with `workspace_id` from Step 1 and this `initial_message`:

```
Build a compliance web app called KAIROS for Indian micro-merchants.

Visual design system (match closely, this is not a generic dashboard look):
- Background: warm off-white/cream, #F2F0EA — not pure white.
- Text and primary buttons: near-black, #111111.
- Accent: chartreuse, #D7FF3F. Used sparingly — only for the single
  highest-emphasis call-to-action on a screen and for positive highlights.
  Never used as a background fill or for secondary elements.
- Headlines: Space Grotesk, bold weight, large size, tight letter-spacing,
  often uppercase.
- Body text: Inter.
- Buttons: fully rounded (pill-shaped). Primary actions are black fill with
  white text. The single top CTA per screen is chartreuse fill with black
  text.
- Cards: light gray #F5F5F2 (one step off the page background), rounded
  corners, generous padding. Stat cards follow: icon, then a large bold
  number, then a small gray caption underneath.
- This is a compliance/risk tool, not an investment app — keep the bold
  editorial feel of the palette and type, but the content and tone should
  read as a serious business compliance product.

Backend: all data comes from a Flask API at https://kairos-api-i8rt.onrender.com.
Call it through a Supabase edge function that proxies requests server-side —
do not call it directly from browser client code.

Build the first screen: Onboarding & Profile Setup.
- A form with: Legal Business Name (text input), Trade Style (text input),
  Business Category (text input), and a Tax Structure control that toggles
  between "Regular GST Scheme" and "Composition Scheme" — style this as a
  two-option segmented control, not a checkbox or dropdown.
- On page load, GET /profile and populate the form from the response. The
  response has keys: legal_business_name, trade_style, business_category,
  tax_scheme (value is either "regular" or "composition").
- A Save button (this screen's top CTA — chartreuse) that POSTs the form
  values as JSON to /profile and shows a success confirmation on completion.
- Below the form, a "System Integrations" section with three status badges
  in a row: "SMS Forwarding Tunnel" (shown as connected/green), "Email
  Invoices" (shown as not connected/gray), "Historical ITR Uploads" (shown
  as not connected/gray). These three badges are static/visual only for now
  — no live status check.
```

- [ ] **Step 3: Show build progress**

Call `render_project_widget` with the `projectId` returned from Step 2.

- [ ] **Step 4: Review the diff**

Call `get_diff` on the project. Confirm: the palette/type/button/card rules from the design system are actually applied (not defaulted to a generic template look), the profile form fields match the four listed, and the API calls target `/profile` as specified.

- [ ] **Step 5: If the diff doesn't match, send a follow-up**

If anything is off (wrong colors, missing segmented control, calling the API from client code instead of an edge function), send a `send_message` follow-up describing exactly what to fix, then repeat Steps 3-4.

---

### Task 9: Multi-Channel Ingestion Hub

**Depends on:** Task 8 (same Lovable project, `projectId` from Task 8 Step 2).

- [ ] **Step 1: Send the build message**

Call `send_message` on the Task 8 project with:

```
Add a second screen: Multi-Channel Ingestion Hub. Use the same design system
as the Onboarding screen (cream background #F2F0EA, chartreuse #D7FF3F CTA
accent, Space Grotesk headlines, Inter body, pill buttons, light-gray
#F5F5F2 cards).

Sections on this screen:
1. Digital File Intake — a drag-and-drop file uploader accepting PDFs and
   images (receipts/invoices/e-invoices). On drop or file select, POST the
   file as multipart/form-data (field name "file") to /scan. Show the
   returned transaction (vendor, amount) and any findings as a confirmation
   once the upload completes.
2. Optical Imaging — a live web camera capture panel (getUserMedia) for
   photographing a physical receipt or cash slip. On capture, POST the
   captured image the same way, to /scan.
3. Live Ambient Streams — a list showing recent SMS-sourced transactions.
   GET /transactions?source=sms and render each as a compact row (vendor,
   amount, timestamp). Also show a WhatsApp channel in this section, but
   visually disabled/"coming soon" — no live data for it.
4. Historical Baselines — a file upload area for prior-year ITR filings,
   labeled to seed long-term compliance trends. This is upload-only for
   now (no processing) — accept a file selection and show a "received,
   processing" confirmation state, but don't wire it to any endpoint yet.

Route real API calls (/scan, /transactions) through the same Supabase edge
function proxy pattern as the Onboarding screen.
```

- [ ] **Step 2: Review**

Call `get_diff`, then `render_project_widget`. Confirm the drag-and-drop and camera capture both call `/scan` correctly, the SMS stream calls `/transactions?source=sms`, and the WhatsApp/historical-ITR sections are visually present but clearly non-functional stubs (not silently pretending to work).

- [ ] **Step 3: Follow up if needed**

Same pattern as Task 8 Step 5 — send a `send_message` correction if the diff doesn't match, then re-review.

---

### Task 10: Risk Triage Ledger

**Depends on:** Task 8.

- [ ] **Step 1: Send the build message**

```
Add a third screen: Risk Triage Ledger — this is the app's command center,
so give it the most visual weight of the four screens.

1. Main Transaction Ledger — a searchable, sortable table. GET /transactions
   and render each row with: vendor_name, amount, payment_mode, timestamp,
   and classification (business/personal — style these as a small tag per
   row so the business/personal split is visually obvious at a glance). Add
   a text search box that filters rows client-side by vendor_name.
2. Triage Flag Matrix — GET /findings and group them into three visually
   distinct zones by severity:
   - Red zone, "Statutory Violations" — findings with severity "red" (e.g.
     type "cash_limit_breach"). Highest visual priority.
   - Yellow zone, "Anomalies & Audits" — findings with severity "yellow"
     (type "vendor_risk").
   - Green zone, "Deduction Harvesting" — findings with severity "green"
     (type "deduction_opportunity").
   Each finding shows its message and its reasons (a list of short strings)
   — the reasons should be visible, not hidden behind a click, since showing
   the reasoning behind every flag (not a black-box score) is a core product
   principle.

Use the same design system as the other screens. The red/yellow/green
severity colors are semantic status colors for this matrix only — don't let
them bleed into the rest of the UI, which stays cream/black/chartreuse.
```

- [ ] **Step 2: Review**

Call `get_diff`, then `render_project_widget`. Confirm the three severity zones are visually distinct, findings show their `reasons` list (not just the summary message), and the search box filters the ledger table.

- [ ] **Step 3: Follow up if needed**

Same pattern as before.

---

### Task 11: Prescriptive Action & Tax Automation

**Depends on:** Task 8.

- [ ] **Step 1: Send the build message**

```
Add a fourth screen: Prescriptive Action & Tax Automation.

1. Interactive Remediation — on each finding shown in the Risk Triage
   Ledger's flag matrix, add two actions: a "Get advice" button that POSTs
   to /findings/{id}/advice (empty JSON body {} is fine) and displays the
   returned "answer" text inline, and a "Dismiss" toggle that PATCHes
   /findings/{id} with {"acknowledged": true} and visually marks that
   finding as handled (e.g. greyed out / moved to a "reviewed" section).
2. ITR Pre-Filing Risk Audit — GET /itr/export and display it as a summary
   panel: gross_business_receipts, total_business_expenses,
   section_40A3_disallowed, deductions_found (an object with keys 80C, 80D,
   24b), and vendor_risk_flags, each as its own stat card in the established
   card style (icon, big number, small caption).
3. Automated Export Engine — a single top CTA button (chartreuse) labeled
   something like "Generate ITR Export" that calls the same GET /itr/export
   endpoint and offers the JSON response as a downloadable file.

Every LLM-derived answer or suggestion anywhere in the app (not just this
screen) should visibly end with or be labeled "worth reviewing with your CA"
— this app gives guidance, not confident tax advice, and that framing needs
to be consistently visible, not just present in the raw API text.
```

- [ ] **Step 2: Review**

Call `get_diff`, then `render_project_widget`. Confirm the advice/dismiss actions are wired to the right endpoints with the right HTTP methods (POST vs PATCH), the ITR summary panel's numbers match the stat-card pattern, and the "worth reviewing with your CA" framing is visibly present.

- [ ] **Step 3: Follow up if needed**

Same pattern as before.

---

### Task 12: End-to-end verification and deploy

**Depends on:** Tasks 8-11.

- [ ] **Step 1: Drive the full flow live**

Using `render_project_widget` (or the project's `preview_url`), walk through: fill and save the Onboarding form → confirm `GET /profile` on reload reflects the save. Upload a document via the Ingestion Hub → confirm it appears in the Risk Triage Ledger. Toggle the Onboarding profile to "Composition Scheme," upload another document → confirm no new `vendor_risk` finding appears for it (composition-scheme skip working end-to-end through the real deployed API, not just in Phase A's tests). Click "Get advice" on a finding → confirm real LLM-backed text appears. Click "Generate ITR Export" → confirm the numbers match what's in the ledger.

- [ ] **Step 2: Check for console errors**

If a browser-driving tool is available in this environment, check the console for errors during the above flow. If not, ask the user to do a manual pass and report anything broken.

- [ ] **Step 3: Deploy**

Call `deploy_project` on the project. Report the `preview_url` (or production URL) to the user.

- [ ] **Step 4: Commit a pointer in the KAIROS repo**

`~/KAIROS` doesn't contain the Lovable frontend code (it lives in Lovable's own project), but record the link for future reference:

```bash
cd ~/KAIROS
```

Append to `README.md`, replacing the `## Setup` section's context (add a new section after it):
```markdown
## Frontend

The production UI is built in Lovable (React/Tailwind), not this repo's
`ui_app.py` (Streamlit is now a fallback/local demo tool only). Lovable
project: <insert editor_url from create_project's response here>. It calls
this repo's Flask API (deployed to Render at
https://kairos-api-i8rt.onrender.com) through Supabase edge functions.
```

```bash
git add README.md
git commit -m "docs: note the Lovable frontend and its relationship to this repo"
git push origin main
```

---

## Self-Review Notes

- **Spec coverage:** Architecture's new routes (Task 1-3, 5-7) ✓. Auth/single-business (no task changes storage to per-user — confirmed absent by design) ✓. Visual design system (Global Constraints + repeated verbatim in every Phase B prompt) ✓. All four screens (Tasks 8-11) ✓, each with explicit real-vs-stubbed treatment matching the spec (WhatsApp and historical-ITR-parsing explicitly built as visual stubs, not silently omitted or silently faked). Data flow (spec's five bullet points) ✓ — each maps onto a task: profile→Task 2, scan→Task 4, ledger→Task 3, remediation→Tasks 6-7, export→Task 5. Testing section ✓ (Phase A: TDD throughout; Phase B: explicitly not unit-tested, verified live in Task 12, matching the spec's stated approach). Deployment section ✓ (Render already live, Task 7 Step 6 push triggers redeploy with the full Phase A surface).
- **Placeholder scan:** no TBD/TODO; every Lovable message is the actual prompt text to send, not a description of what to send.
- **Type consistency:** `process_scan`'s transaction/finding shapes match `process_sms`'s and `ui_app.process_scanned_document`'s exactly (same keys: `id`, `timestamp`, `source`, `raw_text`, `classification`, `amount`, `payment_mode`, `vendor_name`, `vendor_gstin`, `invoice_number`, `category_hint`). `storage.update_finding`'s signature (`finding_id, updates, path=None`) matches how Task 6 Step 4 calls it in the `PATCH` route. `profile.load_profile()["tax_scheme"]` check is written identically in Task 4 Step 3 (`webhook_app.py`) and Step 4 (`ui_app.py`).
