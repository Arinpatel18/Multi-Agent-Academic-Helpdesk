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
    args = ap.parse_args()

    out = ROOT / "eval" / "results" / f"{args.model.replace(':', '-').replace('/', '_')}__{args.mode}"
    out.mkdir(parents=True, exist_ok=True)
    os.environ["HELPDESK_LOG_DIR"] = str(out)
    os.environ["HELPDESK_DRAFTS_DIR"] = str(out / "email_drafts")
    warnings.filterwarnings("ignore")
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    from helpdesk.runner import Helpdesk  # import after env vars are set

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
                r = await desk.ask(q["question"])  # fresh session per question
                r.update(id=q["id"], run=k, model=args.model)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                print(f"[run {k}] {q['id']} {r['latency_s']:6.1f}s {r['answered_by']}: {r['answer'][:90]!r}", flush=True)

    asyncio.run(run())


if __name__ == "__main__":
    main()
