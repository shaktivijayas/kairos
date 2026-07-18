# KAIROS Lovable Frontend — Design

## Purpose

Replace the current Streamlit UI with a custom-designed frontend built in Lovable
(React/Tailwind), matching the visual language of a reference case study
("Fintra" — a Behance case study for an investment platform by Emote agency).
Streamlit's fixed widget chrome can't deliver this level of custom design
without reading as "Streamlit wearing a costume" — a real frontend framework
is required to avoid a generic/AI-slop result.

The frontend expands KAIROS from its current MVP (SMS webhook + camera-scan
dashboard) into four screens: Onboarding & Profile Setup, Multi-Channel
Ingestion Hub, Risk Triage Ledger, and Prescriptive Action & Tax Automation.

## Architecture

The Lovable frontend never calls the Python backend directly from the
browser — it goes through Lovable's own Supabase edge functions (server-side),
which proxy to the deployed Flask API at `https://kairos-api-i8rt.onrender.com`.
This matches Lovable's normal integration pattern and keeps the backend URL
out of client-side JS.

`kairos/` (rules engine, storage, Gemma wrapper, ITR export) is untouched —
it's the proven, tested core. `webhook_app.py` gains real REST routes beyond
the existing `/sms`:

- `GET /transactions` (supports an optional `?source=sms|camera` filter, used
  by the Ingestion Hub's live SMS stream), `GET /findings` — power the Risk
  Triage Ledger
- `POST /scan` — camera/file upload → `llm.read_document_image` (already
  mime-type flexible, so this handles both photos and PDFs) → the same
  scoring pipeline `ui_app.py` already runs
- `GET /itr/export` — wraps `itr_export.export_itr_json` (also backs the
  "pre-filing risk audit" view — same underlying data, different framing)
- `GET /profile`, `POST /profile` — new: business metadata + tax scheme,
  via a new `kairos/profile.py` module (single JSON file — see Auth below)
- `POST /findings/<id>/advice` — wraps `llm.answer_question` for
  remediation guidance
- `PATCH /findings/<id>` — mark a finding acknowledged/dismissed

## Auth

Single-business, no login. There is no user/account concept anywhere in the
current backend, and the hackathon/demo context doesn't need one. All storage
(`ledger.jsonl`, `findings.jsonl`, the new `profile.json`) remains a single
shared file, not scoped per-user. Real multi-tenant accounts (Supabase Auth,
per-user storage) are explicitly out of scope for this pass.

## Visual Design System

Extracted from the Fintra reference images:

- **Background**: warm off-white/cream (`#F2F0EA`), not pure white.
- **Ink**: near-black (`#111111`) for text and primary buttons.
- **Accent**: chartreuse (`#D7FF3F`) — used sparingly, only for primary CTAs
  and positive highlights, never as a background fill.
- **Typography**: heavy geometric sans for display headlines (large, tight
  tracking, often all-caps) + a clean grotesk for body text. The actual
  Fintra typeface is proprietary/unknown, so this uses **Space Grotesk**
  (headlines) + **Inter** (body) — same geometric-bold character, freely
  available via Google Fonts.
- **Buttons**: fully-rounded (pill) — black-fill/white-text for primary
  actions, chartreuse-fill/black-text for the single highest-emphasis CTA
  per screen.
- **Cards**: light gray (`#F5F5F2`) rounded containers, generous padding,
  icon + big bold number + small gray caption pattern (from the "Our
  Achievements" stat-card panel in the reference).
- **Semantic colors**: red/yellow/green are used *only* inside the Triage
  Flag Matrix as status colors — they don't compete with chartreuse, which
  stays the brand/CTA color everywhere else.

## Screens: Real vs. Stubbed

Scoped deliberately — real, working logic for everything we already have
proven backend support for; clearly-marked stubs for the rest, so nothing is
silently overpromised.

### 1. Onboarding & Profile Setup
- Business name, trade style, category, GST scheme toggle — **real**.
  Backed by `kairos/profile.py` + `/profile` GET/POST, single JSON file.
- The scheme toggle has a real effect: when `tax_scheme == "composition"`,
  `score_vendor_risk` is skipped entirely (composition-scheme businesses
  can't claim ITC, so vendor ITC risk doesn't apply to them). Deeper
  composition-scheme logic (CMP-08 filing, turnover-limit tracking) is
  **out of scope**.
- Integration status badges: SMS forwarding shows **real** live/last-seen
  status (real SMS already flow through `/sms`). Email invoices and
  historical ITR uploads show a **static "not connected"** state — no
  ingestion pipeline exists for either.

### 2. Multi-Channel Ingestion Hub
- Drag-and-drop file upload (PDF/e-invoice/receipt) and live camera capture
  — **real**, both hit `POST /scan`.
- Live SMS stream — **real** (`GET /transactions?source=sms`). WhatsApp
  interception — **stubbed**: shown as a disabled "coming soon" channel, no
  WhatsApp Business API integration exists.
- Historical ITR upload — **stubbed**: file is accepted and stored, but
  nothing parses it into compliance trends.

### 3. Risk Triage Ledger
- Searchable ledger (business/personal split, vendor/amount/payment
  mode/date) and the red/yellow/green flag matrix — **fully real**. Maps
  directly onto `GET /transactions` / `GET /findings` and the `severity`
  field the rules engine already produces. Least invention needed of the
  four screens.

### 4. Prescriptive Action & Tax Automation
- Remediation buttons — **real, but scoped differently than the original
  pitch implied**: since a flagged transaction already happened, there's
  nothing to mechanically "fix." The button instead calls
  `POST /findings/<id>/advice` (genuine LLM-backed guidance via
  `answer_question`) plus a simple acknowledge/dismiss state via
  `PATCH /findings/<id>`. Auto-drafted vendor dispute messages (from the
  original hackathon pitch) are **out of scope** for this pass.
- ITR pre-filing risk audit and one-click export — **fully real**, both
  re-frame `itr_export.export_itr_json`'s existing output.

## Data Flow

- Onboarding form → `POST /profile` → `profile.json`.
- Camera/file upload → `POST /scan` → `read_document_image` →
  `score_vendor_risk` (skipped if composition scheme) + `find_deductions` →
  `ledger.jsonl` / `findings.jsonl`.
- Ledger screen → `GET /transactions` + `GET /findings`, rendered directly.
- Remediation button → `POST /findings/<id>/advice` or
  `PATCH /findings/<id>`.
- Export button → `GET /itr/export` → `itr_export.export_itr_json`.

## Testing

New Flask routes follow the same TDD pattern as the existing `/sms` route —
Flask test client + mocked `llm` calls (see `tests/test_webhook_app.py`).
`kairos/profile.py` gets unit tests matching `storage.py`'s style
(tmp_path-based roundtrip tests). The composition-scheme rule change (skip
`score_vendor_risk`) gets a test in `tests/test_rules.py`. The Lovable-side
React UI is not unit-tested — verified by driving it live, the same
approach used for the Streamlit UI earlier in this project.

## Implementation Note

This spec covers two execution modes that don't fit one plan format: the
backend routes are ours to write directly (TDD, exact file paths, like every
prior task in this project), while the Lovable frontend is built by Lovable's
own agent via MCP messages describing each screen against this design system
— we don't hand-write that React code. The implementation plan should treat
these as two phases: backend routes first (so real data exists to build
against), then the Lovable screens.

## Deployment

Flask API is already deployed to Render (`https://kairos-api-i8rt.onrender.com`,
verified live end-to-end: real Gemma call + Section 40A(3) rule reproduced in
production). Known gap: `storage.py`/`profile.py` write to local disk, which
Render's free tier wipes on every new deploy (no persistent volume on that
tier) — acceptable for now, flagged as a future need if data must survive
across deploys.
