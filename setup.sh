#!/usr/bin/env bash
# One-time setup: Python env, Ollama models, vector store.  Usage: ./setup.sh
set -euo pipefail
cd "$(dirname "$0")"

PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
echo "Using $PY ($($PY --version))"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

command -v ollama >/dev/null || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }
curl -s http://localhost:11434/api/tags >/dev/null || { echo "Start Ollama first (open the app or run: ollama serve)"; exit 1; }
for m in nomic-embed-text ${HELPDESK_MODELS:-qwen3:8b llama3.1:8b}; do
  echo "Pulling $m"; ollama pull "$m"
done

.venv/bin/python -m helpdesk.ingest --reset
echo "Setup complete. Try:  .venv/bin/python -m helpdesk.cli --trace"
