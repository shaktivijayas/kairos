# KAIROS (Aegis-Triage) — Project Configuration Design

## Purpose

A compliance assistant for India's ERP-free micro-merchants, freelancers, and gig
workers, whose business and personal spending co-mingle on a single UPI-linked
phone. Every existing compliance tool requires ERP integration or a GSTN portal
login, which structurally excludes this segment. KAIROS works instead, and
purely, off two ambient inputs: forwarded banking SMS alerts and photographed
paper invoices/slips.

It is dual-direction: it defends against statutory exposure (Section 40A(3) daily
cash limits, Section 16 input tax credit loss from a vendor's own non-compliance)
and it surfaces unclaimed deductions the business qualifies for but doesn't know
about (80C, 80D, 24b, composition scheme / Udyam-linked benefits). It also
answers decision-time questions ("should I pay this vendor in cash?") before the
action is taken, not just after scanning a document post-hoc. All risk/opportunity
flags show their reasoning rather than a black-box score, and outputs are framed
as "worth reviewing with your CA," not confident tax advice.

## Architecture

Two independent local Python processes, sharing one internal package so the SMS
path and the camera-scan path funnel into the same parsing/rules/storage logic
instead of duplicating it:

- **`webhook_app.py`** (Flask) — single POST endpoint receiving forwarded SMS
  text (Android SMS-forwarder app → ngrok tunnel → this endpoint). Thin adapter:
  parse → classify → check → store.
- **`ui_app.py`** (Streamlit) — demo-facing app: camera input for invoice/slip
  photos, a chat box for "is this okay" questions, and a dashboard of the ledger,
  risk alarms, and deduction findings.
- **`kairos/`** — shared internal package imported by both processes.

Both processes run locally during the demo, launched together via `run.sh`.

## Components (`kairos/`)

- **`config.py`** — loads `.env`; holds constants (`CASH_LIMIT_INR = 10000`,
  `GEMMA_MODEL = "gemma-3-27b-it"`).
- **`llm.py`** — wrapper around the Google AI Studio API, calling **Gemma 3**
  (`gemma-3-27b-it`) exclusively — no fallback/switch to another model, to keep
  config simple. Three functions:
  - `classify_transaction(text)` — personal vs. business
  - `read_document_image(image_bytes)` — multimodal invoice/slip parsing
  - `answer_question(question, context)` — the "is this okay" chat
- **`storage.py`** — append/read `data/ledger.jsonl` (transactions/documents) and
  `data/findings.jsonl` (risk/deduction flags). JSON Lines on disk, no database.
- **`rules.py`** — pure-Python statutory engine, **no LLM calls**: cash-limit
  aggregation (§40A(3)), vendor ITC risk scoring with explainable reasons,
  deduction matching (80C/80D/24b). Being LLM-free makes this the one module
  that's unit-testable without hitting any API or camera.
- **`itr_export.py`** — maps the ledger + findings into ITR-1/ITR-4 JSON field
  schema.

## Data Flow

- SMS → `webhook_app.py` → `llm.classify_transaction` → `rules.check_cash_limit`
  → `storage.append` → alarm if breached.
- Camera photo → `ui_app.py` → `llm.read_document_image` →
  `rules.score_vendor_risk` + `rules.find_deductions` → `storage.append`.
- Chat question → `ui_app.py` → `llm.answer_question` (fed relevant
  rules/ledger context) → plain-language answer, no storage write.
- "Generate my return" → `itr_export.py` reads the full ledger → structured
  JSON mapped to ITR-1/ITR-4 fields.

## Configuration Files

- **`requirements.txt`**: `flask`, `streamlit`, `google-genai`, `python-dotenv`,
  `pandas`, `pyngrok`.
- **`.env.example`**: `GEMINI_API_KEY=`, `NGROK_AUTHTOKEN=`, `CASH_LIMIT_INR=10000`.
  Real `.env` stays gitignored.
- **`.gitignore`**: existing Node.js-template file already ignores `.env`;
  add Python-specific entries (`__pycache__/`, `*.pyc`, `.venv/`, `venv/`) and
  ignore `data/*.jsonl` (runtime ledger data, not committed).
- **`data/`**: empty at commit time (`.gitkeep`); `storage.py` writes
  `ledger.jsonl` / `findings.jsonl` here at runtime.
- **`README.md`**: pitch, architecture diagram, run instructions (`./run.sh`,
  or the two commands it wraps), ngrok setup step.
- **`run.sh`**: launches `webhook_app.py` (which starts the ngrok tunnel itself
  via `pyngrok`) in the background, then runs `streamlit run ui_app.py` in the
  foreground; traps `SIGINT` to kill the background webhook process on exit.

## Testing

- `tests/test_rules.py` covers `rules.py` only — pure Python, no API or camera
  dependency, the one module practically unit-testable before a hackathon
  deadline.
- The LLM- and camera-dependent paths (`llm.py`, the Streamlit camera flow, the
  SMS webhook) are validated by manual demo run-through, not automated tests.

## Out of Scope (for this pass)

- No SQLite/real database — JSON Lines on disk, per explicit choice.
- No model fallback/switching between Gemma and Gemini — Gemma 3 only.
- No production deployment story (auth, hosting, multi-user) — this is a local,
  single-device hackathon demo configuration.
