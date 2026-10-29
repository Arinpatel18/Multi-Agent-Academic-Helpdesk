"""Run the question set through the helpdesk and store raw traces.

    python eval/run_eval.py --model qwen3:8b --mode multi --runs 3
    python eval/run_eval.py --model llama3.1:8b --mode multi --runs 3
    python eval/run_eval.py --model qwen3:8b --mode single --runs 1

Results go to eval/results/<model>__<mode>/run<k>.jsonl. Re-running resumes where it stopped.
Each configuration gets its own unanswered-question log and email-draft folder.
"""
import argparse
import asyncio
import json
import logging
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--mode", choices=["multi", "single"], default="multi")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--ids", nargs="*", help="only these question ids")
    ap.add_argument("--delay", type=float, default=0, help="seconds to pause between questions (API rate limits)")
    args = ap.parse_args()

    out = ROOT / "eval" / "results" / f"{args.model.replace(':', '-').replace('/', '_')}__{args.mode}"
    out.mkdir(parents=True, exist_ok=True)
    os.environ["HELPDESK_LOG_DIR"] = str(out)
    os.environ["HELPDESK_DRAFTS_DIR"] = str(out / "email_drafts")
    warnings.filterwarnings("ignore")
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    from helpdesk.runner import Helpdesk  # import after env vars are set
    from helpdesk.tools import log_unanswered_question

    transient = ("ratelimit", "rate limit", "429", "rate_limit", "timeout", "serviceunavailable", "503",
                 "internalservererror", "apiconnectionerror")

    async def ask_with_retry(desk, question, attempts=5):
        """Retry API rate-limit/transient failures so they are not scored as wrong answers."""
        for i in range(attempts):
            r = await desk.ask(question, auto_log=False)
            err = (r["error"] or "").lower().replace(" ", "")
            if not any(t.replace(" ", "") in err for t in transient):
                break
            if "perday" in err or "tokensperday" in err or "(tpd)" in err:
                raise SystemExit(f"Daily API quota exhausted: {r['error'][:300]}\nRe-run the same command later to resume.")
            wait = 30 * (i + 1)
            print(f"   transient API error, retrying in {wait}s: {r['error'][:120]}", flush=True)
            await asyncio.sleep(wait)
        else:
            raise SystemExit(f"Giving up after {attempts} attempts: {r['error'][:300]}\nRe-run to resume.")
        if r["refused"] and not r["logged_by_agent"]:
            # same safety net as Helpdesk.ask, applied only to the final (non-transient) attempt
            log_unanswered_question(question, "auto-logged: agent could not answer")
            r["auto_logged"] = True
        return r

    questions = json.loads((ROOT / "eval" / "questions.json").read_text())
    if args.ids:
        questions = [q for q in questions if q["id"] in args.ids]

    async def run():
        desk = Helpdesk(args.mode, args.model)
        for k in range(1, args.runs + 1):
            path = out / f"run{k}.jsonl"
            done = {json.loads(l)["id"] for l in open(path)} if path.exists() else set()
            for q in questions:
                if q["id"] in done:
                    continue
                r = await ask_with_retry(desk, q["question"])  # fresh session per question
                r.update(id=q["id"], run=k, model=args.model)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                print(f"[run {k}] {q['id']} {r['latency_s']:6.1f}s {r['tokens']['prompt'] + r['tokens']['completion']:6d} tok "
                      f"{r['answered_by']}: {r['answer'][:90]!r}", flush=True)
                if args.delay:
                    await asyncio.sleep(args.delay)

    asyncio.run(run())


if __name__ == "__main__":
    main()
