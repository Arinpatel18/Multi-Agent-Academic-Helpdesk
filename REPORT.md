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

We built an IIT Jodhpur academic helpdesk with Google ADK, Ollama models (through ADK's LiteLLM connector), and a ChromaDB RAG pipeline over 27 documents. A single-agent baseline was extended to a multi-agent system: an orchestrator transfers each question to a **policy**, **schedule** or **email** agent. We evaluated it on 30 questions, with 3 repeated runs per multi-agent configuration.

**Models.** We evaluated the two 8B models the assignment suggests, **Qwen3 8B** and **Llama 3.1 8B**. For comparison, we also ran the same study with two smaller models: **Qwen3-4B-Instruct (4B)** and **Llama 3.2 (3B)** (§4.1). All configurations used identical code, documents and questions.

Key results:

| Configuration | Accuracy | Correct & grounded | Out-of-scope refused | False refusals | Routing |
|---|---|---|---|---|---|
| **Multi-agent, qwen3:8b** (3 runs) | **82%** | **79%** | **100%** | 11% | 97% |
| **Multi-agent, llama3.1:8b** (3 runs) | **81%** | **81%** | **100%** | **0%** | **100%** |
| Single-agent, qwen3:8b (1 run) | 79% | 79% | 100% | 17% | – |
| Multi-agent, qwen3-4b-instruct (3 runs) | 88% (86% after manual review) | 88% | 100% | 8% | 100% |
| Single-agent, qwen3-4b-instruct (1 run) | 50% | 50% | 100% | 33% | – |
| Multi-agent, llama3.2:3b (3 runs) | 39% | 38% | 100% | 36% | 64% |

* **Out-of-scope questions were refused 100% of the time in every configuration**, and every refusal reached the human-review log.
* **Replacing the LLM at 8B (Qwen3 → Llama 3.1) gives the same accuracy (82% vs 81%) but different failures.** Llama never refuses an answerable question and always logs refusals itself, but often replies without the content (empty email replies). Qwen sometimes refuses without searching.
* **Model size matters most for weak tool-callers.** Llama goes from 39% (3B) to 81% (8B). Qwen3-4B-Instruct (88%) matches or beats Qwen3 8B (82%), because it is a newer release tuned for instruction following and tool use.
* **The multi-agent design helps small models most.** It adds +38 points for the 4B model (50% → 88%), but only +3 points for Qwen3 8B (79% → 82%), which already chooses tools well as a single agent.
* **Answers vary between runs.** Across 3 runs, qwen3:8b changed the outcome on 3 questions and llama3.1:8b on 4 (§5.5).

## 2. System

| Part | Implementation |
|---|---|
| Framework | Google ADK 2.13: `LlmAgent`, `sub_agents` + `transfer_to_agent`, `Runner`, `InMemorySessionService` |
| LLM | Ollama through `LiteLlm("ollama_chat/<model>")`, temperature 0.2, context 8192. Qwen3 "thinking" mode off |
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

### 4.1 Models

| Models | Role |
|---|---|
| `qwen3:8b`, `llama3.1:8b` | Main study: the 8B models the assignment suggests. Llama 3.1 is the replacement LLM for Qwen3 |
| `qwen3:4b-instruct-2507` (4-bit), `llama3.2:3b` | Smaller-model comparison: the same study at 4B and 3B parameters |

For the 4B model we used the `qwen3:4b-instruct-2507` build. The plain `qwen3:4b` build is thinking-only: it ignored `think=false` and was about 8× slower per question.

All six configurations used the same code, documents, vector index settings and questions.

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

* **Accuracy**: an in-scope answer is correct if it matches every required fact pattern (regex). Answers that passed because they contain the right number were also **reviewed manually** (§5.5).
* **Groundedness**: the answer cites an expected source document *and* that document was actually returned by a tool call in the same run. This catches invented citations.
* **Correct & grounded**: both of the above.
* **Correct refusal**: an out-of-scope question was refused. **Logged by agent**: the agent itself called `log_unanswered_question`.
* **False refusal**: an in-scope question was refused or left unanswered.
* **Routing**: the final answer came from an expected agent.
* **Changes across runs**: the correct/refused/answering-agent outcome flipped, or the answer text similarity fell below 0.9.

**One ground-truth correction.** Reviewing the 8B results showed that doc 32 (the current IITJ specialisation page) contains the same credit table as the 2019 regulations: "B.Tech. (Regular) … Open Electives (OE) 10". Every model cited doc 32 for P02, which is correct, but our expected-source list for P02 originally named only doc 01. We added doc 32 and re-scored **all** configurations with the same file. This raised the 4B model's groundedness from 83% to 88%, and changed no accuracy number.

## 5. Results

### 5.1 Overall

**Accuracy** (in-scope questions, all runs pooled):

| Configuration | Runs | Overall | Policy | Schedule | Email | Grounded | Correct & grounded |
|---|---|---|---|---|---|---|---|
| qwen3:8b, multi | 3 | 82% (59/72) | 79% | 90% | 75% | 86% | 79% |
| llama3.1:8b, multi | 3 | 81% (58/72) | 92% | 76% | 50% | 94% | 81% |
| qwen3:8b, single | 1 | 79% (19/24) | 69% | 100% | 75% | 83% | 79% |
| qwen3-4b-instruct, multi | 3 | 88% (63/72) | 85% | 86% | 100% | 88% | 88% |
| qwen3-4b-instruct, single | 1 | 50% (12/24) | 46% | 71% | 25% | 67% | 50% |
| llama3.2:3b, multi | 3 | 39% (28/72) | 44% | 43% | 17% | 50% | 38% |

**Refusals and routing:**

| Configuration | Out-of-scope refused | Out-of-scope logged by agent | False refusals | Routing |
|---|---|---|---|---|
| qwen3:8b, multi | 100% (18/18) | 0% | 11% | 97% |
| llama3.1:8b, multi | 100% (18/18) | 100% | 0% | 100% |
| qwen3:8b, single | 100% (6/6) | 0% | 17% | – |
| qwen3-4b-instruct, multi | 100% (18/18) | 0% | 8% | 100% |
| qwen3-4b-instruct, single | 100% (6/6) | 0% | 33% | – |
| llama3.2:3b, multi | 100% (18/18) | 100% | 36% | 64% |

**Email drafts.** The accuracy score requires the draft (instructor address, request type) to appear in the reply. Separately, we checked whether `draft_email` actually saved a correct draft for E01–E03:

| Configuration | Correct draft saved | Correct draft also shown in the reply |
|---|---|---|
| qwen3:8b, multi | 9/9 | 6/9 |
| llama3.1:8b, multi | 8/9 | 3/9 |
| qwen3:8b, single | 2/3 | 2/3 |
| qwen3-4b-instruct, multi | 9/9 | 9/9 |
| qwen3-4b-instruct, single | 1/3 | 1/3 |
| llama3.2:3b, multi | 0/9 | 0/9 |

Both 8B models drafted the right email almost every time. Their low email scores come mostly from replies that do not show the draft, not from wrong drafts.

**The five assignment example questions** (P01, P02, S01, S02, E01) were answered correctly and with citations in all runs by:
* **qwen3:8b multi-agent:** all five, all 3 runs.
* **qwen3-4b-instruct multi-agent:** all five, except P02 run 1 (§5.5).
* **llama3.1:8b:** answered P01, P02, S01 and S02 in all runs, but in every run its E01 reply left out the draft. The draft itself was saved correctly.

### 5.2 Replacing the LLM at 8B: qwen3:8b vs. llama3.1:8b

Overall accuracy is nearly identical (82% vs 81%), but the two models fail in opposite ways.

**llama3.1:8b** is the better *policy* agent (92%), with the best grounding (94%):
* It never refused an answerable question.
* It called `log_unanswered_question` itself for every out-of-scope question (18/18). qwen3:8b relied on the safety net for those.

Its failures are in what it writes back:
* **Empty or incomplete replies (7 answers).** It called the right tool, then replied with only a `Source:` line (E01, E03, S05), so the student never sees the draft or the course list.
* **Tool call printed as text (E02, run 3).** It wrote `draft_email('Deep Learning', ...)` as text instead of calling the tool.
* **Invented schedule (S04, all 3 runs).** It said Computer Vision is "CSL7570, slot I, Mon/Wed/Fri 10–11 AM", without calling `get_slot_timing`. The correct answer is CSL7360, slot H, Mon/Wed 14:00–15:20.
* **Unsupported inference (P13).** It answered "2023" from roll-number prefixes in the spreadsheet chunks, when the correct year is 2020 (§5.4).

**qwen3:8b** is the better *schedule* agent (90%). Its failures are refusing too early:
* **Refusing without searching:**
  * **P09 (Summer 2026 major exam dates), 3 of 3 runs:** the policy agent refused without calling the search tool.
  * **P11 (prerequisites), 2 of 3 runs:** same behaviour.
* **Orchestrator refusal (P13, 3 of 3 runs).** The orchestrator treated the AI&DS start-year question as out of scope. This was the only routing error (97%). It is still better than inventing a year.
* **Invented timing (S04, 2 of 3 runs).** Same failure as Llama: it gave a time without calling the slot tool.
* **One invented citation (S07, run 1).** It cited `log_entry_2026-07-15.csv`, which does not exist. This was the only citation to a non-existent file across all six configurations.

### 5.3 Single agent vs. multi-agent

| Model | Single | Multi | Gain |
|---|---|---|---|
| qwen3-4b-instruct | 50% | 88% | +38 |
| qwen3:8b | 79% | 82% | +3 |

The 4B single agent's failures were all tool-selection problems:
* **No tool call at all (6 policy questions: P02, P05, P08, P09, P10, P13).** It refused immediately without searching.
* **Bypassing the email tool (E01, E02).** It wrote the email itself, so the draft has no instructor address and was not saved.
* **Wrong tool (E04, S07).** For E04 it used `lookup_course` instead of `get_instructor_contact`. For S07 it searched the curricula instead of the course list.

The 8B single agent handles a seven-tool instruction much better, with 100% on schedule questions. It still skipped the search on P08, P09 and P13, and drafted E02 for the wrong course (CSL7570 instead of Deep Learning).

**Conclusion:** splitting the task into small agents with 2–5 tools each matters most when the model is weak at choosing tools. For an 8B model it is a small gain in accuracy. The bigger benefit at that size is a clearer structure: the routing traces show which agent and which tool produced each answer.

### 5.4 Groundedness and refusals

* **Citations were almost always real.** Across all 420 answers, only one citation named a file outside the dataset (qwen3:8b, S07, run 1). Every other cited source was a real document, and every expected-source citation counted as grounded had actually been returned by a tool in that run.
* **Unsupported inference (P13).** For "In which year did the B.Tech AI&DS start?", retrieval returned only spreadsheet chunks, not the programme list. Three behaviours appeared:
  * **qwen3-4b-instruct and llama3.1:8b (multi-agent)** "inferred" 2023 from roll-number prefixes in all 3 runs.
  * **qwen3:8b** and both single-agent runs refused.
  * The correct answer is **2020** (doc 31).
  This is the one question where a retrieval miss led models beyond their sources.
* **Logging needs the safety net.** The Qwen models (4B and 8B) almost never called the logging tool. The only calls were qwen3:8b's three P13 refusals, and none were for an out-of-scope question. They printed the refusal sentence ("…I have logged your question…") without making the call, so their refusals reached the log through the runner's safety net. Both Llama models called the tool for every out-of-scope question. **Logging must not depend on the model's cooperation.**
* **Out-of-scope refusals: 100% in every configuration (84/84).** Read this together with the false-refusal rate: llama3.2:3b's 100% partly reflects refusing too much in general (36% false refusals). llama3.1:8b reaches 100% with 0% false refusals.

### 5.5 Questions whose answers changed across runs

| Configuration | Outcome changed (correct / refused / agent) | Text changed only |
|---|---|---|
| qwen3:8b, multi | **P11, S04, S07** | P01, P04 |
| llama3.1:8b, multi | **E02, E03, S01, S05** | E01, E04, P01, P02, P04, P13, S02 |
| qwen3-4b-instruct, multi | none | P01, **P02**, P04, P13, S02 |
| llama3.2:3b, multi | **E01, E04, P03, P11** | P06, P10 |
| single-agent configurations | 1 run each, not measured | – |

**qwen3:8b:**
* **P11:** refused in 2 runs, answered correctly in 1.
* **S04:** invented time in 2 runs, correct in 1.
* **S07:** refused in runs 1–2. Run 3 answered "not offered", which is correct. Scored correct in all 3 runs, because "I don't know" is accepted for a course that doesn't exist.

**llama3.1:8b:**
* **E02:** correct in runs 1–2; the tool call was printed as text in run 3.
* **E03:** draft shown in 1 run, empty reply in 2.
* **S01:** correct in all runs, but in run 2 it added "timings are not available", which the refusal detector counts as a refusal.
* **S05:** list shown in 1 run, empty reply in 2.

**qwen3-4b-instruct, P02:** changed substantively. In run 1 it read the wrong table row and gave the 10 open-elective credits that count toward a *minor*. Runs 2–3 correctly answered "10 OE credits for a regular B.Tech". The regex accepted all three because each contains "10". After manual review, run 1 is wrong, so its **manual accuracy is 62/72 = 86%**.

**llama3.2:3b:**
* **E01:** transfer printed as text in some runs.
* **E04:** answered in 2 of 3 runs.
* **P03:** correct in 1 of 3 runs.
* **P11:** routed to the schedule agent in one run and to the policy agent in the others.

All other text-only changes were rephrasings with the same facts. We manually checked every 8B answer that passed because it contained a number (P01, P02, P05, P06, P07, P10, P12, S02, S03, S05): **all were genuinely correct**, so no 8B score needed adjustment.

### 5.6 A conflict between the documents (P06)

The **2019 regulations** (doc 01, p.16) say a student needs **100 credits by the end of the 6th semester** to opt for a minor. The **current IITJ web page** (doc 32) says **85 graded credits by the end of the 5th semester**. Qwen models (4B and 8B) consistently answered with the newer rule from doc 32. llama3.1:8b consistently answered with the 2019 rule from doc 01. Both answers were accepted, since each is grounded. A production helpdesk should prefer the newest source and flag the conflict to the student.

### 5.7 Development iterations

Traces are kept in `eval/dev_iterations/`. The first trial run (on the 4B model) exposed three problems, which were fixed before any reported run:

1. **Padded search queries.** The model added "IIT Jodhpur academic regulations" to its queries. Those words appear in every chunk, which drowned the useful terms and caused misses on P03 and P05. Fix: strip these filler phrases from queries, and instruct the agent to use short keyword queries and search a second time before giving up.
2. **Make-up exam rule misrouted.** P04, a question about the make-up exam *rule*, was sent to the email agent. Fix: route a question to the email agent only when the user explicitly asks for an email.
3. **Fuzzy matching too loose.** A unit test showed that "Quantum Machine Learning" resolved to "Machine Learning". Fix: stricter title matching.

## 6. Reproducing the results

```
# 4B/3B study: setup pulls the models and builds the index
./setup.sh
./run_evaluation.sh

# 8B study
HELPDESK_MODELS="qwen3:8b llama3.1:8b" ./setup.sh
MAIN=qwen3:8b ALT=llama3.1:8b ./run_evaluation.sh

# re-score every configuration in eval/results/
.venv/bin/python eval/score.py
```

Each `run_evaluation.sh` call runs the main model as a multi-agent system ×3, the replacement model ×3, and the main model as a single agent ×1. Runs are resumable.

## 7. Limitations and future work

* **Scoring:** the regex scorer is strict on facts but can accept a right number given for the wrong reason (P02, 4B). Manual review or an LLM judge is needed for a final number. It also counts a correct draft as wrong when the reply doesn't show it (§5.1).
* **Reconstructed CSVs:** the current-semester CSVs are reconstructions, so schedule results show tool use, not real timetable accuracy.
* **Tool skipping (qwen3:8b P09/P11, schedule S04 for both 8B models):** could be fixed by requiring a tool call on a specialist's first turn (ADK `tool_config` mode `ANY`), or by having the runner call `search_academic_documents` / `get_slot_timing` directly before the LLM answers.
* **Empty replies (llama3.1:8b):** the email agent could return the tool's draft text verbatim. That is a deterministic fix: it does not rely on the model restating the draft.
* **Logging:** make logging fully deterministic. Any route to the refusal path writes to the log in code, which is already true through the safety net.
* **Retrieval:** add a cross-encoder reranker and table-aware PDF parsing. Several facts sit in flattened tables (credit structure, grade points), and adding the year and title as metadata would favour the newest source when documents conflict (P06). The P13 miss also suggests boosting the programme-list document for "when did programme X start" questions.
