"""Entry point for the ADK developer UI:  adk web   (run from the repository root)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from helpdesk.agents import build_multi_agent  # noqa: E402

root_agent = build_multi_agent()
