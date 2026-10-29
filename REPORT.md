# Multi-Agent Academic Helpdesk: Evaluation Report

**Team members**

| Name | Roll number |
|---|---|
| Balijapalli Arin Patel | B23CM1009 |
| Bure Siddardha | B23CM1011 |
| Aarav Dawer Bhojwani | B23CM1002 |
| Kanishk Singh Dayma | B23CS1024 |

**Repository:** https://github.com/Arinpatel18/Multi-Agent-Academic-Helpdesk
**Raw traces and full tables:** `eval/results/` (`RESULTS.md`, `per_question.csv`, `run*.jsonl`)

## 1. Summary

We built an IIT Jodhpur academic helpdesk with Google ADK, Ollama models (through ADK's LiteLLM connector), and a ChromaDB RAG pipeline over 27 documents. A single-agent baseline was extended to a multi-agent system: an orchestrator transfers each question to a **policy**, **schedule** or **email** agent. We evaluated it on 30 questions, with 3 repeated runs per configuration.

**Resource constraints:** the assignment suggests 8B models on a 16 GB machine. Our only available machine was an **Apple M1 Mac with 8 GB RAM**, where an 8B model could not run at a usable speed. We therefore used a **4B-parameter model (Qwen3-4B-Instruct)** as the main model, and a 3B model (Llama 3.2) for the model-replacement comparison (§4.1). The code supports 8B models unchanged.

Key results:

| Configuration | Accuracy | Correct & grounded | Correct refusals (out-of-scope) | False refusals | Routing |
|---|---|---|---|---|---|
| **Multi-agent, qwen3-4b-instruct** (3 runs) | **88%** (86% after manual review) | **83%** | **100%** | **8%** | **100%** |
| Single-agent, qwen3-4b-instruct (1 run) | 50% | 50% | 100% | 33% | – |
| Multi-agent, llama3.2:3b (3 runs) | 39% | 38% | 100% | 36% | 64% |

* With the **same model**, the **multi-agent design raises accuracy from 50% to 88%**. Smaller, focused instructions and tool sets make a 4B model choose the right tool far more reliably.
* **Out-of-scope questions were always refused (100%)** in every configuration, and every refusal ended up in the human-review log.
* **Replacing the LLM matters as much as the architecture.** llama3.2:3b over-refuses and often emits tool calls as plain text, which drops accuracy to 39%.
* **qwen3-4b-instruct never changed a correct/incorrect outcome across 3 runs.** The wording changed on 5 questions, and one of those changes (P02, run 1) was substantive.

## 2. System

| Part | Implementation |
|---|---|
| Framework | Google ADK 2.13: `LlmAgent`, `sub_agents` + `transfer_to_agent`, `Runner`, `InMemorySessionService` |
| LLM | Ollama through `LiteLlm("ollama_chat/<model>")`, temperature 0.2, context 8192 |
| Embeddings | `nomic-embed-text` (Ollama), with `search_document:` / `search_query:` prefixes |
| Vector store | ChromaDB (cosine). Page-aware chunks of about 1,200 characters with 200 overlap: 2,226 chunks from 24 documents |
| Retrieval | Hybrid: dense top-20 + BM25 top-20, fused with Reciprocal Rank Fusion; top 6 returned with `file, page` citations |
| Agents | `helpdesk_orchestrator` → `policy_agent` (rules, curriculum, calendar), `schedule_agent` (slots, offerings, counts), `email_agent` (contacts, drafts) |
| Tools | `search_academic_documents`, `lookup_course`, `list_offered_courses`, `get_slot_timing`, `get_instructor_contact`, `draft_email` (saved to disk, never sent), `log_unanswered_question` |
| Unanswered log | `logs/unanswered_questions.jsonl`. The agents call the tool, and the runner adds a safety net that logs any refusal the model did not log itself |

The single-agent baseline (`--mode single`) is one `LlmAgent` with all seven tools and a combined instruction.

## 3. Data

**27 documents** (manifest and source URLs: `data/README.md`):

* **24 real IITJ documents**, downloaded from the public Office of Academics pages:
  * UG/PG academic regulations (2019 and 2022)
  * a 2020 amendment notification
  * circulars on the AIIMS joint programmes and M.S. by Research
  * academic calendars for AY 2025-26, AY 2026-27 and Summer 2026
  * 11 curricula and course booklets
  * the first-year slot-system spreadsheet
  * three web pages: UG registration guidelines, the programme list, and specialisations/minors
* **3 structured CSVs** for the current semester's course offerings, slot timetable and faculty directory. The real versions are only on the IITJ intranet, so these were reconstructed in the official format: real course titles and HSS course codes, with **dummy instructor names and emails**.

**Personal data removed:**
* Faculty names and emails in the slot spreadsheet were replaced with dummies.
* A roll-number list was dropped.
* Duplicates and scanned PDFs with no text layer were also removed.

## 4. Evaluation method

### 4.1 Resource constraints: 4B model on an M1 Mac

The assignment targets 8B models on a 16 GB machine. Due to resource constraints, all experiments were run on an **Apple M1 Mac with 8 GB of unified memory**. We tried `qwen3:8b` first: its 5.2 GB of weights plus the context cache did not fit alongside the operating system, so the machine swapped heavily and generated **0.02 tokens/s** (one 30-token answer took 24 minutes).

We therefore used the **4B-parameter `qwen3:4b-instruct-2507` (4-bit, about 3.8 GB)** as the main model. It runs fully on the M1 GPU at 10–40 s per question. The model-replacement comparison uses `llama3.2:3b`. The code defaults to `qwen3:8b`, and `./run_evaluation.sh` reproduces the full study with `qwen3:8b` and `llama3.1:8b` on a 16 GB machine (§6).

We also had to choose the qwen3 build carefully. Plain `qwen3:4b` is a thinking-only build: it ignored `think=false` and took about 200 s per question. `qwen3:4b-instruct-2507` needs about 20–30 s.

### 4.2 Question set (`eval/questions.json`)

30 questions with ground-truth answers verified against the documents, plus the expected source and the expected agent for each:

| Category | n | Examples |
|---|---|---|
| Policy (RAG) | 13 | attendance for the major exam, open-elective credits, make-up deadline, grade points, minor eligibility, exam dates, M.Tech max duration, course prerequisites |
| Schedule (CSV) | 7 | slot of Autonomous Systems, number of 400-level HSS electives, instructor of CSL7570, class timings, a non-existent course |
| Email | 4 | leave email for CSL7570, make-up exam request, sick leave with name and roll number, instructor email ID |
| Out of scope | 6 | dining, reaching campus, IPL, Wi-Fi password, JEE closing rank, mess fee |

All five example questions from the assignment are included (P01, P02, S01, S02, E01).

### 4.3 Metrics (`eval/score.py`)

* **Accuracy**: an in-scope answer is correct if it matches every required fact pattern (regex). Text changes across runs were also **reviewed manually** (§5.5).
* **Groundedness**: the answer cites an expected source document *and* that document was actually returned by a tool call in the same run. This catches invented citations.
* **Correct & grounded**: both of the above.
* **Correct refusal**: an out-of-scope question was refused. **Logged by agent**: the agent itself called `log_unanswered_question`.
* **False refusal**: an in-scope question was refused or left unanswered.
* **Routing**: the final answer came from an expected agent.
* **Changes across runs**: the correct/refused/answering-agent outcome flipped, or the answer text similarity fell below 0.9.

## 5. Results

### 5.1 Overall

**Accuracy** (in-scope questions, all runs pooled):

| Configuration | Runs | Overall | Policy | Schedule | Email | Grounded | Correct & grounded |
|---|---|---|---|---|---|---|---|
| qwen3-4b-instruct, multi | 3 | 88% (63/72) | 85% | 86% | 100% | 83% | 83% |
| qwen3-4b-instruct, single | 1 | 50% (12/24) | 46% | 71% | 25% | 67% | 50% |
| llama3.2:3b, multi | 3 | 39% (28/72) | 44% | 43% | 17% | 50% | 38% |

**Refusals, routing and speed:**

| Configuration | Out-of-scope refused | Out-of-scope logged by agent | False refusals | Routing | Mean latency |
|---|---|---|---|---|---|
| qwen3-4b-instruct, multi | 100% (18/18) | 0% | 8% | 100% | 25.9 s |
| qwen3-4b-instruct, single | 100% (6/6) | 0% | 33% | – | 21.5 s |
| llama3.2:3b, multi | 100% (18/18) | 100% | 36% | 64% | 11.6 s |

qwen3-4b-instruct multi-agent answered the five assignment example questions correctly and with citations in all 3 runs, except P02 (correct in 2 of 3):

* **75% attendance:** students below it may still appear (01_Academic_Regulations p.7).
* **10 open-elective credits:** in 2 of 3 runs (see §5.5).
* **Autonomous Systems:** slot J.
* **400-level HSS electives:** 5.
* **CSL7570 leave email:** a draft to the instructor's address, saved to disk.

### 5.2 Single agent vs. multi-agent (same model)

The multi-agent version is **38 points more accurate** and has **4× fewer false refusals**. The single agent's failures were all tool-selection problems:

* **No tool call at all (6 policy questions: P02, P05, P08, P09, P10, P13).** It refused immediately without searching the documents, even though the multi-agent policy agent answered all of them except P13.
* **Bypassing the email tool (E01, E02).** It wrote the email itself instead of calling `draft_email`, so the draft has no instructor address and was not saved.
* **Wrong tool (E04, S07).**
  * **E04:** it called `lookup_course` instead of `get_instructor_contact` and replied that the email ID "is not available".
  * **S07:** it searched the curricula instead of the course-offering list.

With 7 tools and one long instruction, a 4B model loses track of which tool to use. With 2–5 tools and a short, role-specific instruction per agent, it rarely does.

### 5.3 Replacing the LLM (qwen3-4b-instruct → llama3.2:3b)

llama3.2:3b's errors break down into three groups:

* **Over-refusal at the orchestrator (21 of 72 in-scope answers).** It classified grading, exam dates and programme questions as out of scope.
* **Tool calls emitted as text (9 answers).** For example, E01 returned the literal string `{"type":"function","function":"email_agent",...}` instead of a real transfer. As a result, no email draft was ever saved.
* **Empty answers (11).** A specialist called the right tool and then replied with only `Source: course_offerings…csv` (S05, S06, S07).

Its 100% out-of-scope refusal rate is partly a side effect of refusing too much. It should be read together with its 36% false-refusal rate. It was, however, the only model that called `log_unanswered_question` itself.

### 5.4 Groundedness and refusals

* **Citations were real.** For qwen multi, every answer that cited the expected source cited a document the tools had actually returned in that run. No citation was invented.
* **One unsupported inference (P13).** For "In which year did the B.Tech AI&DS start?", retrieval returned only spreadsheet chunks. The model "inferred" 2023 from roll-number prefixes instead of refusing. The correct answer is 2020, from doc 31. This was the only answer that went beyond its sources.
* **Logging relies on the safety net for qwen.** The qwen orchestrator never called the logging tool: it printed the refusal sentence ("…I have logged your question…") without making the call. All 24 qwen refusals still reached the log through the runner's safety net. **Logging must not depend on the model's cooperation.**
* **Specialist refusal without searching (P11, S04).** In all 3 runs, the specialist refused without calling any tool and printed a fake `log_unanswered_question(...)` as text. Both questions are answerable.

### 5.5 Questions whose answers changed across runs

| Config | Outcome changed (correct/refused/agent) | Text changed only |
|---|---|---|
| qwen3-4b-instruct, multi | none | P01, **P02**, P04, P13, S02 |
| llama3.2:3b, multi | **E01, E04, P03, P11** | P06, P10 |
| qwen3-4b-instruct, single | (1 run, not measured) | – |

* **P02 (qwen) changed substantively.** In run 1 the model read the wrong table row and answered with the 10 open-elective credits that count toward a *minor*. Runs 2–3 correctly answered "10 OE credits for a regular B.Tech". The regex scorer accepted all three runs because each contains "10". After manual review, run 1 is wrong, so **manual accuracy is 62/72 = 86%**.
* **P01, P04, P13 and S02 (qwen)** were rephrasings with the same facts.
* **llama3.2:3b:**
  * **E01:** the transfer was emitted as text in some runs.
  * **E04:** answered in 2 of 3 runs.
  * **P03:** correct in 1 of 3 runs.
  * **P11:** routed to the schedule agent in one run and to the policy agent in the others.

### 5.6 A conflict between the documents (P06)

The **2019 regulations** (doc 01, p.16) say a student needs **100 credits by the end of the 6th semester** to opt for a minor. The **current IITJ web page** (doc 32) says **85 graded credits by the end of the 5th semester**. The agent consistently answered with the newer rule and cited doc 32. Both answers were accepted, since each is grounded. A production helpdesk should prefer the newest source and flag the conflict to the student.

### 5.7 Development iterations

Traces are kept in `eval/dev_iterations/`. The first trial run exposed three problems, which were fixed before the reported runs:

1. **Padded search queries.** The model added "IIT Jodhpur academic regulations" to its queries. Those words appear in every chunk, which drowned the useful terms and caused misses on P03 and P05. Fix: strip these filler phrases from queries, and instruct the agent to use short keyword queries and search a second time before giving up.
2. **Make-up exam rule misrouted.** P04, a question about the make-up exam *rule*, was sent to the email agent. Fix: route a question to the email agent only when the user explicitly asks for an email.
3. **Fuzzy matching too loose.** A unit test showed that "Quantum Machine Learning" resolved to "Machine Learning". Fix: stricter title matching.

## 6. Running with 8B models

Because of the resource constraints in §4.1, the 8B configurations were not evaluated. The system is not tied to the 4B model: the default model is `qwen3:8b`, and on a 16 GB machine one command reproduces the full study with the assignment's suggested models:

```
./setup.sh            # dependencies, qwen3:8b + llama3.1:8b + embeddings, index
./run_evaluation.sh   # qwen3:8b multi x3, llama3.1:8b multi x3, single x1, scoring
```

We expect 8B models to reduce the two main failure types we saw: skipped tool calls (qwen 4B) and over-refusal or tool calls printed as text (llama 3B). Both are known weaknesses of small models at tool calling.

## 7. Limitations and future work

* **Scoring:** the regex scorer is strict on facts but can accept a right number given for the wrong reason (P02). Manual review or an LLM judge is needed for a final number.
* **Reconstructed CSVs:** the current-semester CSVs are reconstructions, so schedule results show tool use, not real timetable accuracy.
* **Tool skipping (P11, S04, single-agent P05):** could be fixed by requiring a tool call on a specialist's first turn (ADK `tool_config` mode `ANY`), or by having the runner call `search_academic_documents` directly before the LLM answers.
* **Logging:** make logging fully deterministic. Any route to the refusal path writes to the log in code, which is already true through the safety net.
* **Retrieval:** add a cross-encoder reranker and table-aware PDF parsing. Several facts sit in flattened tables (credit structure, grade points), and adding the year and title as metadata would favour the newest source when documents conflict.
* **Model choice:** a stronger tool-calling model (8B) should reduce both the over-refusal seen with llama3.2:3b and qwen's skipped tool calls. §6 gives the commands to run this comparison on a 16 GB machine.
