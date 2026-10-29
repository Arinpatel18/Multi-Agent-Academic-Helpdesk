#!/usr/bin/env bash
# Full evaluation used in the report. Resumable: re-run to continue after an interruption.
#   ./run_evaluation.sh                                  # the reported setup: 4B main model, 3B replacement
#   MAIN=qwen3:8b ALT=llama3.1:8b ./run_evaluation.sh    # optional: 8B models on a 16 GB machine
set -euo pipefail
cd "$(dirname "$0")"
MAIN=${MAIN:-qwen3:4b-instruct-2507-q4_K_M}
ALT=${ALT:-llama3.2:3b}
RUNS=${RUNS:-3}

.venv/bin/python eval/run_eval.py --model "$MAIN" --mode multi  --runs "$RUNS"   # multi-agent, repeated runs
.venv/bin/python eval/run_eval.py --model "$ALT"  --mode multi  --runs "$RUNS"   # replaced LLM
.venv/bin/python eval/run_eval.py --model "$MAIN" --mode single --runs 1         # single-agent baseline
.venv/bin/python eval/score.py
