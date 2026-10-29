"""Run a question through the single- or multi-agent helpdesk and return a structured trace."""
import asyncio
import re
import time
import uuid
from datetime import datetime

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .agents import build_multi_agent, build_single_agent
from .tools import log_unanswered_question

APP = "iitj_academic_helpdesk"
REFUSAL_RE = re.compile(r"(don'?t|do not|does not|doesn'?t) (know|have)|not (able|possible) to (find|answer)|"
                        r"(couldn'?t|could not|cannot|can'?t|unable to) (find|answer|help|locate)|outside (what|the scope)|"
                        r"no information|not (available|covered|mentioned) in", re.I)
_THINK = re.compile(r"<think>.*?</think>", re.S)


class Helpdesk:
    def __init__(self, mode="multi", model=None):
        self.mode = mode
        agent = build_multi_agent(model) if mode == "multi" else build_single_agent(model)
        self.sessions = InMemorySessionService()
        self.runner = Runner(app_name=APP, agent=agent, session_service=self.sessions)

    async def new_session(self, user_id="student"):
        s = await self.sessions.create_session(app_name=APP, user_id=user_id, session_id=str(uuid.uuid4()))
        return s.id

    async def ask(self, question, session_id=None, user_id="student", auto_log=True):
        session_id = session_id or await self.new_session(user_id)
        msg = types.Content(role="user", parts=[types.Part(text=question)])
        t0 = time.time()
        agents, tool_calls, texts, error = [], [], [], None
        try:
            async for ev in self.runner.run_async(user_id=user_id, session_id=session_id, new_message=msg):
                if ev.author and ev.author != "user" and (not agents or agents[-1] != ev.author):
                    agents.append(ev.author)
                for part in (ev.content.parts if ev.content and ev.content.parts else []):
                    if part.function_call:
                        tool_calls.append({"agent": ev.author, "name": part.function_call.name,
                                           "args": dict(part.function_call.args or {})})
                    elif part.function_response and tool_calls:
                        for tc in reversed(tool_calls):
                            if tc["name"] == part.function_response.name and "response" not in tc:
                                tc["response"] = part.function_response.response
                                break
                    elif part.text and not part.thought and ev.author != "user":
                        texts.append((ev.author, part.text))
        except Exception as e:  # keep the evaluation running if one call fails
            error = f"{type(e).__name__}: {e}"
        final_author = texts[-1][0] if texts else None
        answer = "\n".join(t for a, t in texts if a == final_author).strip()
        answer = _THINK.sub("", answer).split("</think>")[-1].strip()  # drop leaked reasoning
        refused = bool(REFUSAL_RE.search(answer)) or not answer
        logged = any(tc["name"] == "log_unanswered_question" for tc in tool_calls)
        auto_logged = False
        if auto_log and refused and not logged:
            # Safety net: every refusal must reach the human-review log even if the model forgot the tool.
            log_unanswered_question(question, "auto-logged: agent could not answer" + (f" ({error})" if error else ""))
            auto_logged = True
        return {
            "question": question, "answer": answer, "mode": self.mode, "agents": agents,
            "answered_by": final_author, "tool_calls": tool_calls, "refused": refused,
            "logged_by_agent": logged, "auto_logged": auto_logged, "error": error,
            "latency_s": round(time.time() - t0, 1), "timestamp": datetime.now().isoformat(timespec="seconds"),
        }


def ask_sync(question, mode="multi", model=None):
    return asyncio.run(Helpdesk(mode, model).ask(question))
