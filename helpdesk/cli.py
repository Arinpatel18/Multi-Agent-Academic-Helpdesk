"""Interactive command-line chat with the helpdesk.

    python -m helpdesk.cli                       # multi-agent, interactive
    python -m helpdesk.cli --mode single         # single-agent baseline
    python -m helpdesk.cli -q "What is the slot for Autonomous Systems?" --trace
"""
import argparse
import asyncio
import json
import logging
import warnings

from . import config
from .runner import Helpdesk


def show(result, trace):
    print(f"\n[{result['answered_by']}] {result['answer']}\n")
    if trace:
        print(f"  route: {' -> '.join(result['agents'])} | {result['latency_s']}s")
        for tc in result["tool_calls"]:
            print(f"  tool: {tc['agent']}.{tc['name']}({json.dumps(tc['args'], ensure_ascii=False)})")
        if result["auto_logged"] or result["logged_by_agent"]:
            print(f"  logged to {config.UNANSWERED_LOG.relative_to(config.ROOT)}")
        if result["error"]:
            print(f"  error: {result['error']}")
        print()


async def main():
    ap = argparse.ArgumentParser(description="IIT Jodhpur Academic Helpdesk")
    ap.add_argument("--mode", choices=["multi", "single"], default="multi")
    ap.add_argument("--model", default=config.CHAT_MODEL, help="Ollama model name, e.g. qwen3:4b, llama3.1:8b")
    ap.add_argument("-q", "--question", help="ask one question and exit")
    ap.add_argument("--trace", action="store_true", help="print routing and tool calls")
    args = ap.parse_args()

    desk = Helpdesk(args.mode, args.model)
    if args.question:
        show(await desk.ask(args.question), args.trace)
        return
    session = await desk.new_session()
    print(f"IIT Jodhpur Academic Helpdesk ({args.mode}-agent, {args.model}). Type 'exit' to quit.")
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("exit", "quit"):
            break
        if q:
            show(await desk.ask(q, session_id=session), args.trace)


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)
    asyncio.run(main())
