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
