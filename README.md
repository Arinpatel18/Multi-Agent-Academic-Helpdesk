# IIT Jodhpur Academic Helpdesk — Multi-Agent RAG System

A local, multi-agent academic helpdesk built with **Google ADK** and **Ollama** models (accessed through ADK's LiteLLM connector), with a **ChromaDB** RAG pipeline over 27 IIT Jodhpur documents. It can:

* answer questions on academic programmes, rules and regulations, curricula/course contents and the academic calendar, **with citations** (file + page);
* answer slot / timetable / course-offering / instructor questions from CSV files;
* draft emails to course instructors (leave, sick leave, make-up exam). Drafts are saved for review, **never sent**;
* **refuse** out-of-scope questions (dining, travel, …) instead of guessing, and **log every unanswered question** for a human to follow up.

Everything runs offline on a 16 GB laptop.

## Architecture

```
                         user question
                               │
                 ┌─────────────▼──────────────┐
                 │   helpdesk_orchestrator     │  routes with transfer_to_agent
                 │   tool: log_unanswered_q    │  out-of-scope → refuse + log
                 └──┬──────────┬──────────┬────┘
        ┌───────────▼──┐ ┌─────▼────────┐ ┌▼─────────────┐
        │ policy_agent │ │schedule_agent│ │ email_agent  │
        │ search_docs  │ │ lookup_course│ │ draft_email  │
        │ log_unans.   │ │ list_offered │ │ get_instr.   │
        │              │ │ get_slot     │ │ log_unans.   │
        │              │ │ search_docs  │ │              │
        └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
               │                │                │
     ChromaDB + BM25     course_offerings.csv   faculty_directory.csv
     (24 documents,      slot_timetable.csv     outputs/email_drafts/
      2,226 chunks)
```

| Component | Implementation |
|---|---|
| Agent framework | Google ADK 2.13 (`LlmAgent`, `sub_agents` + `transfer_to_agent`, `Runner`) |
| LLM | Ollama via `LiteLlm("ollama_chat/<model>")`. Default `qwen3:8b` (alt. `llama3.1:8b`) for 16 GB; `qwen3:4b-instruct-2507-q4_K_M` / `llama3.2:3b` for 8 GB |
| Embeddings | `nomic-embed-text` via Ollama (with `search_document:` / `search_query:` prefixes) |
| Vector store | ChromaDB (persistent, cosine), page-aware chunks of ~1,200 chars with 200 overlap |
| Retrieval | Hybrid: dense top-20 + BM25 top-20, fused with Reciprocal Rank Fusion → top 5 |
| Unanswered log | `logs/unanswered_questions.jsonl`, written by the agents' tool **plus** a runner safety net that logs any refusal the model forgot to log |

### Tools (`helpdesk/tools.py`)

| Tool | Purpose |
|---|---|
| `search_academic_documents(query)` | Hybrid RAG search; returns passages with `file, page` citations |
| `lookup_course(course)` | Course by code or (fuzzy) title → slot, instructor, credits, … |
| `list_offered_courses(department, level, course_type)` | Filter **and count** courses floated this semester |
| `get_slot_timing(slot)` | Slot → days and times |
| `get_instructor_contact(course)` | Course → instructor name, email, office |
| `draft_email(course, request_type, reason, num_days, start_date, student_name, roll_number)` | Builds an email draft to the instructor and saves it to `outputs/email_drafts/` |
| `log_unanswered_question(question, reason)` | Appends to the human-review log |

## Repository layout

```
helpdesk/            config.py, ingest.py (RAG indexing), retrieval.py (hybrid search),
                     tools.py, agents.py (single + multi agent), runner.py, cli.py
helpdesk_agent/      ADK entry point for `adk web`
data/documents/      24 real IITJ documents (PDF / XLSX / MD)
data/structured/     course offerings, slot timetable, faculty directory (CSV)
data/README.md       document manifest and provenance
eval/questions.json  30 evaluation questions with ground truth and expected sources
eval/run_eval.py     runs a model/mode N times and stores full traces
eval/score.py        computes metrics → eval/results/RESULTS.md
REPORT.md / REPORT.pdf evaluation report (PDF built with scripts/md2pdf.py)
```

## Setup (macOS / Linux, 16 GB RAM)

1. Install [Ollama](https://ollama.com/download) and start it (open the app, or `ollama serve`).
2. Run the setup script. It creates `.venv` (Python 3.11 or 3.12), installs requirements, pulls `nomic-embed-text`, `qwen3:8b` and `llama3.1:8b`, and builds the vector store:

```bash
chmod +x setup.sh run_evaluation.sh
./setup.sh
```

**Windows (PowerShell)**: do the same steps by hand:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
ollama pull nomic-embed-text; ollama pull qwen3:8b; ollama pull llama3.1:8b
.venv\Scripts\python -m helpdesk.ingest --reset
```

On an **8 GB** machine 8B models swap heavily and become unusably slow. Use small models instead:
`HELPDESK_MODELS="qwen3:4b-instruct-2507-q4_K_M llama3.2:3b" ./setup.sh` and
`export HELPDESK_MODEL=qwen3:4b-instruct-2507-q4_K_M`. (Avoid plain `qwen3:4b`: it is a thinking-only build and ~8x slower.)

## Usage

```bash
# interactive chat (multi-agent), showing routing and tool calls
.venv/bin/python -m helpdesk.cli --trace

# one question
.venv/bin/python -m helpdesk.cli -q "What is the slot for the course Autonomous Systems?" --trace

# single-agent baseline / another model
.venv/bin/python -m helpdesk.cli --mode single --model llama3.1:8b

# ADK developer web UI (from the repo root)
.venv/bin/adk web
```

Example:

```
You: Write an email to the course instructor of CSL7570 that I need leave for 2 days
[email_agent] To: pranav.iyer@iitj-dummy.ac.in
Subject: Leave Application - CSL7570 Information Retrieval
Dear Dr. Pranav Iyer, I would like to request leave from the CSL7570 (Information Retrieval) classes for 2 days ...
(draft saved to outputs/email_drafts/, not sent)
Source: course_offerings_AY2026-27_Sem1.csv; faculty_directory.csv
```

Unanswered questions are in `logs/unanswered_questions.jsonl` (one JSON object per line: timestamp, question, reason, status).

### Using a hosted API instead of a local model

If no 16 GB machine is available, the **same 8B models** can be called through a hosted API.
Embeddings and ChromaDB stay local. Any model name with a provider prefix is passed straight to LiteLLM:

```bash
export OPENROUTER_API_KEY=...        # https://openrouter.ai/keys
.venv/bin/python eval/run_eval.py --model openrouter/qwen/qwen3-8b --mode multi --runs 3
.venv/bin/python eval/run_eval.py --model openrouter/meta-llama/llama-3.1-8b-instruct --mode multi --runs 3

export GROQ_API_KEY=...              # https://console.groq.com/keys
.venv/bin/python -m helpdesk.cli --model groq/llama-3.1-8b-instant --trace
```

Ollama Cloud works through the local Ollama app (`ollama signin`, then e.g. `--model gpt-oss:20b-cloud`), but it does
not host Qwen3 8B or Llama 3.1 8B. Its smallest models (20B+) are larger than the assignment's 8B target.

### Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `HELPDESK_MODEL` | `qwen3:8b` | Ollama chat model |
| `HELPDESK_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `HELPDESK_TEMPERATURE` | `0.2` | Sampling temperature |
| `HELPDESK_NUM_CTX` | `8192` | Context window passed to Ollama |
| `HELPDESK_THINKING` | `0` | `1` enables qwen3 thinking mode (much slower) |
| `OLLAMA_API_BASE` | `http://localhost:11434` | Ollama server |

## Evaluation

```bash
./run_evaluation.sh          # qwen3:8b multi x3, llama3.1:8b multi x3, qwen3:8b single x1, then scoring
# 8 GB RAM:  MAIN=qwen3:4b-instruct-2507-q4_K_M ALT=llama3.2:3b ./run_evaluation.sh
```

Or step by step:

```bash
.venv/bin/python eval/run_eval.py --model qwen3:8b --mode multi --runs 3
.venv/bin/python eval/score.py           # → eval/results/RESULTS.md, per_question.csv, summary.json
```

Runs are resumable. Each configuration writes full traces (answer, agents visited, every tool call with arguments and responses, latency) to `eval/results/<model>__<mode>/run<k>.jsonl`, plus its own unanswered-question log and email drafts.

Metrics: answer **accuracy** (regex match on required facts), **groundedness** (answer cites an expected source *and* that source was actually returned by a tool), **correct refusal** of out-of-scope questions, whether the agent **logged** them, **false refusals**, **routing** accuracy, latency, and **questions whose outcome changed across runs**. See `REPORT.pdf` (or `REPORT.md`) for findings.
