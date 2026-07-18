# KAIROS

An ambient, ERP-free compliance shield for India's micro-merchants, freelancers, and gig workers. KAIROS reads forwarded banking SMS alerts and photographed invoices — no ERP integration, no GSTN portal login — and flags Section 40A(3) cash-limit breaches, vendor ITC risk, and unclaimed deductions (80C/80D/24b), with reasoning shown for every flag. It also answers "is this okay?" compliance questions before you act.

All outputs are framed as worth reviewing with your CA, not confident tax advice.

## Architecture

- `webhook_app.py` (Flask) — receives forwarded SMS via an ngrok tunnel
- `ui_app.py` (Streamlit) — camera scan, chat, and dashboard
- `kairos/` — shared logic: `llm.py` (Gemma 4), `rules.py` (statutory checks), `storage.py` (JSON Lines ledger), `profile.py` (business metadata), `itr_export.py` (ITR-1/ITR-4 JSON mapping)

## Frontend

The production UI is built in Lovable (React/Tailwind), not this repo's
`ui_app.py` (Streamlit is now a fallback/local demo tool only). Lovable
project: https://lovable.dev/projects/67f5678b-54a6-47fa-86e5-7b8e45f2285c.
Live at https://kairos-compliance.lovable.app. It calls this repo's Flask
API (deployed to Render at https://kairos-api-i8rt.onrender.com) through
Supabase-edge-function-style server-side proxies (TanStack Start
`createServerFn`) — never directly from browser client code.

## Setup

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` (Google AI Studio) and `NGROK_AUTHTOKEN` (ngrok.com)
3. `./run.sh`

This starts the SMS webhook (its ngrok tunnel URL is printed to the console) and the Streamlit UI. Point an Android SMS-forwarder app at the printed ngrok URL + `/sms`.
