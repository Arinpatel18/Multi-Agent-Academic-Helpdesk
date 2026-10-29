#!/usr/bin/env bash
# Full evaluation used in the report. Resumable: re-run to continue after an interruption.
#   ./run_evaluation.sh                 # default: 8B models (16 GB RAM)
#   MAIN=qwen3:4b-instruct-2507-q4_K_M ALT=llama3.2:3b ./run_evaluation.sh   # 8 GB RAM machines
set -euo pipefail
cd "$(dirname "$0")"
MAIN=${MAIN:-qwen3:8b}
ALT=${ALT:-llama3.1:8b}
RUNS=${RUNS:-3}

.venv/bin/python eval/run_eval.py --model "$MAIN" --mode multi  --runs "$RUNS"   # multi-agent, repeated runs
.venv/bin/python eval/run_eval.py --model "$ALT"  --mode multi  --runs "$RUNS"   # replaced LLM
.venv/bin/python eval/run_eval.py --model "$MAIN" --mode single --runs 1         # single-agent baseline
.venv/bin/python eval/score.py
