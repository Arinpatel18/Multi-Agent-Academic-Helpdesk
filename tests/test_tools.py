"""Offline checks for the tools (no chat model needed; retrieval test needs Ollama + built index).

    .venv/bin/python -m pytest -q tests      or      .venv/bin/python tests/test_tools.py
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("HELPDESK_LOG_DIR", tempfile.mkdtemp())
os.environ.setdefault("HELPDESK_DRAFTS_DIR", tempfile.mkdtemp())

from helpdesk import tools  # noqa: E402


def test_lookup_course_by_title_and_code():
    assert tools.lookup_course("Autonomous Systems")["course"]["slot"] == "J"
    assert tools.lookup_course("csl7570")["course"]["course_title"] == "Information Retrieval"
    assert not tools.lookup_course("Quantum Machine Learning")["found"]


def test_count_hss_400_electives():
    r = tools.list_offered_courses("Humanities", 400, "elective")
    assert r["count"] == 5


def test_slot_and_contact():
    assert tools.get_slot_timing("h")["slot"]["days"] == "Mon/Wed"
    assert tools.get_instructor_contact("CSL7570")["instructor"]["email"] == "pranav.iyer@iitj-dummy.ac.in"


def test_draft_email_and_log():
    d = tools.draft_email("CSL7570", "leave", num_days=2)
    assert d["created"] and "pranav.iyer@iitj-dummy.ac.in" in d["draft"] and "2 days" in d["draft"]
    assert tools.log_unanswered_question("dining options?", "out of scope")["logged"]


def test_retrieval_finds_attendance_rule():
    r = tools.search_academic_documents("attendance requirement major exam")
    assert any("75%" in x["text"] for x in r["results"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
