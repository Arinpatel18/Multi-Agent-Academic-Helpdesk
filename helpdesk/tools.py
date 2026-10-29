"""Tools exposed to the agents. ADK turns each function (signature + docstring) into a tool schema.

All tools return plain dicts with a `source` / `citation` field so the agents can cite them.
"""
import difflib
import json
import re
from datetime import datetime
from functools import lru_cache

import pandas as pd

from . import config, retrieval

DEPT_ALIASES = {
    "hss": "Humanities and Social Sciences", "humanities": "Humanities and Social Sciences",
    "cse": "Computer Science and Engineering", "cs": "Computer Science and Engineering", "computer science": "Computer Science and Engineering",
    "ai": "School of Artificial Intelligence and Data Science", "aids": "School of Artificial Intelligence and Data Science",
    "ai&ds": "School of Artificial Intelligence and Data Science", "aide": "School of Artificial Intelligence and Data Science",
    "ee": "Electrical Engineering", "electrical": "Electrical Engineering",
    "me": "Mechanical Engineering", "mechanical": "Mechanical Engineering",
    "maths": "Mathematics", "math": "Mathematics", "physics": "Physics",
    "bb": "Bioscience and Bioengineering", "bio": "Bioscience and Bioengineering",
}


@lru_cache(maxsize=None)
def _csv(path):
    return pd.read_csv(path, dtype=str).fillna("")


def _course_row(course):
    """Find a course by code (exact) or title (fuzzy). Returns a dict or None."""
    df = _csv(config.COURSES_CSV)
    q = course.strip().upper().replace(" ", "")
    hit = df[df.course_code.str.upper() == q]
    if hit.empty:
        titles = df.course_title.str.lower().tolist()
        ql = course.strip().lower()
        exact = [i for i, t in enumerate(titles) if t == ql]
        # query contained in a title ("autonomous" -> "Autonomous Systems"); NOT the reverse, otherwise
        # "Quantum Machine Learning" would wrongly resolve to "Machine Learning"
        sub = [i for i, t in enumerate(titles) if len(ql) >= 4 and ql in t]
        close = difflib.get_close_matches(ql, titles, n=1, cutoff=0.88)
        idx = exact or sub or ([titles.index(close[0])] if close else [])
        if not idx:
            return None
        hit = df.iloc[[idx[0]]]
    return hit.iloc[0].to_dict()


def search_academic_documents(query: str) -> dict:
    """Search the IIT Jodhpur academic document collection (rules & regulations, curricula,
    course contents, academic calendars, circulars, programme lists) and return the most
    relevant passages with their citations. Use this for any question about academic rules,
    credits, grading, attendance, programmes, course contents or academic calendar dates.

    Args:
        query: A focused search query, e.g. "attendance requirement to appear in major exam".
    """
    hits = retrieval.search(query)
    return {
        "results": [{"citation": retrieval.citation(h), "text": h["text"]} for h in hits],
        "instruction": "Answer ONLY from these passages and cite the citation of the passage you used. "
                       "If none of them contains the answer, say you do not know and call log_unanswered_question.",
    }


def lookup_course(course: str) -> dict:
    """Look up a course offered this semester by course code (e.g. "CSL7570") or by title
    (e.g. "Autonomous Systems"). Returns code, title, department, level, credits, L-T-P,
    course type, slot, instructor and classroom.

    Args:
        course: Course code or course title.
    """
    row = _course_row(course)
    if row is None:
        return {"found": False, "message": f"No course matching '{course}' is offered in {config.CURRENT_SEMESTER}.",
                "source": config.COURSES_CSV.name}
    return {"found": True, "semester": config.CURRENT_SEMESTER, "course": row, "source": config.COURSES_CSV.name}


def list_offered_courses(department: str = "", level: int = 0, course_type: str = "") -> dict:
    """List and COUNT the courses offered (floated) this semester, filtered by department,
    course level and/or course type. Use this for questions like "how many 400 level
    electives has the Humanities department floated this semester?".

    Args:
        department: Department name or short form (e.g. "Humanities", "HSS", "CSE", "EE"). Empty for all.
        level: Course level such as 200, 300, 400 or 700. 0 for all levels.
        course_type: Text to match in the course type, e.g. "elective", "core", "open elective". Empty for all.
    """
    df = _csv(config.COURSES_CSV)
    if department:
        d = department.strip().lower()
        full = DEPT_ALIASES.get(d, d)
        df = df[df.department.str.lower().str.contains(re.escape(full.lower()))]
    if level:
        df = df[df.level == str(int(level))]
    if course_type:
        df = df[df.course_type.str.lower().str.contains(re.escape(course_type.strip().lower()))]
    return {
        "semester": config.CURRENT_SEMESTER,
        "filters": {"department": department, "level": level, "course_type": course_type},
        "count": len(df),
        "courses": df[["course_code", "course_title", "department", "level", "course_type", "slot"]].to_dict("records"),
        "source": config.COURSES_CSV.name,
    }


def get_slot_timing(slot: str) -> dict:
    """Return the days and class timings of a timetable slot (e.g. "J", "P1").

    Args:
        slot: Slot label as given in the course list.
    """
    df = _csv(config.SLOTS_CSV)
    hit = df[df.slot.str.upper() == slot.strip().upper()]
    if hit.empty:
        return {"found": False, "message": f"Unknown slot '{slot}'.", "source": config.SLOTS_CSV.name}
    return {"found": True, "slot": hit.iloc[0].to_dict(), "source": config.SLOTS_CSV.name}


def get_instructor_contact(course: str) -> dict:
    """Find the instructor of a course offered this semester and their email ID / office.

    Args:
        course: Course code (e.g. "CSL7570") or course title.
    """
    row = _course_row(course)
    if row is None:
        return {"found": False, "message": f"No course matching '{course}' is offered this semester.",
                "source": config.COURSES_CSV.name}
    fac = _csv(config.FACULTY_CSV)
    f = fac[fac.instructor == row["instructor"]]
    info = f.iloc[0].to_dict() if not f.empty else {"instructor": row["instructor"], "email": "not listed"}
    return {"found": True, "course_code": row["course_code"], "course_title": row["course_title"],
            "instructor": info, "source": f"{config.COURSES_CSV.name}; {config.FACULTY_CSV.name}"}


def draft_email(course: str, request_type: str, reason: str = "", num_days: int = 0,
                start_date: str = "", student_name: str = "", roll_number: str = "") -> dict:
    """Write an email DRAFT (it is NOT sent) from a student to the instructor of a course.
    The instructor's name and email are looked up automatically. The draft is saved to disk
    for the student to review.

    Args:
        course: Course code or title, e.g. "CSL7570".
        request_type: One of "leave", "sick_leave", "makeup_exam", "other".
        reason: Reason / extra details given by the student (e.g. "fever", "missed the minor exam").
        num_days: Number of days of leave, if relevant (0 if not given).
        start_date: Start date of leave or date of the missed exam, if given.
        student_name: Student's name, if given.
        roll_number: Student's roll number, if given.
    """
    contact = get_instructor_contact(course)
    if not contact["found"]:
        return {"created": False, "message": contact["message"]}
    inst = contact["instructor"]
    code, title = contact["course_code"], contact["course_title"]
    name = student_name or "[Your Name]"
    roll = roll_number or "[Roll Number]"
    days = f"{num_days} day{'s' if num_days != 1 else ''}" if num_days else "[number of days]"
    when = f" starting {start_date}" if start_date else ""
    why = reason or "[reason]"
    rt = request_type.lower().replace("-", "_").replace(" ", "_")

    if rt in ("sick_leave", "medical_leave"):
        subject = f"Request for Medical Leave - {code} {title}"
        body = (f"I am writing to inform you that I am unwell ({why}) and will be unable to attend the "
                f"{code} ({title}) classes for {days}{when}. I kindly request you to grant me medical leave "
                f"for this period. I will submit the medical certificate as required and will make up for the "
                f"missed coursework.")
    elif rt in ("makeup_exam", "make_up_exam", "makeup"):
        subject = f"Request for Make-up Examination - {code} {title}"
        body = (f"I was unable to appear for the {code} ({title}) examination{when} due to {why}. "
                f"I kindly request you to permit me to take a make-up examination. I will provide the "
                f"supporting documents required as per the institute regulations.")
    elif rt == "leave":
        subject = f"Leave Application - {code} {title}"
        body = (f"I would like to request leave from the {code} ({title}) classes for {days}{when}"
                f"{' due to ' + why if reason else ''}. I will make sure to cover the material I miss and "
                f"complete any pending work. Kindly grant me leave for this period.")
    else:
        subject = f"Request regarding {code} {title}"
        body = f"I am writing regarding {code} ({title}). {why}"

    text = (f"To: {inst.get('email')}\nSubject: {subject}\n\n"
            f"Dear {inst.get('instructor')},\n\n{body}\n\nThank you for your consideration.\n\n"
            f"Yours sincerely,\n{name}\nRoll No.: {roll}\n")
    config.DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    path = config.DRAFTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}_{code}_{rt}.txt"
    path.write_text(text, encoding="utf-8")
    return {"created": True, "draft": text, "saved_to": path.name,
            "note": "Draft only - not sent. Student should review before sending.", "source": contact["source"]}


def log_unanswered_question(question: str, reason: str) -> dict:
    """Record a question the helpdesk cannot answer (out of scope, or not found in the
    documents) so that a human from the academic office can follow up.

    Args:
        question: The user's question, verbatim.
        reason: Short reason, e.g. "out of scope: dining" or "not found in documents".
    """
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": datetime.now().isoformat(timespec="seconds"), "question": question,
             "reason": reason, "status": "pending_human_review"}
    with open(config.UNANSWERED_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"logged": True, "message": "Question logged for a human to answer."}
