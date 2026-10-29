"""Agent definitions (Google ADK + LiteLLM -> Ollama).

build_single_agent()  : base version - one agent with every tool.
build_multi_agent()   : helpdesk orchestrator that transfers to policy / schedule / email agents.
"""
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from . import config
from .tools import (draft_email, get_instructor_contact, get_slot_timing, list_offered_courses,
                    log_unanswered_question, lookup_course, search_academic_documents)

REFUSAL = ("I'm sorry, I don't know the answer to that. It is outside what the IIT Jodhpur Academic "
           "Helpdesk can answer from its documents, so I have logged your question for a human staff member.")

GROUNDING_RULES = f"""
Rules you must always follow:
- Use ONLY information returned by your tools. Never use your own background knowledge and never guess.
- Every answer must end with a line "Source: <citation>" naming the document/file the tool returned
  (e.g. "Source: 01_Academic_Regulations_Part1_2019.pdf, page 12" or "Source: course_offerings_AY2026-27_Sem1.csv").
- If the tools do not return the information needed, call log_unanswered_question(question, reason) and reply exactly:
  "{REFUSAL}"
- The current semester is {config.CURRENT_SEMESTER}. Keep answers short and factual.
"""

POLICY_INSTRUCTION = """You are the Policy Agent of the IIT Jodhpur Academic Helpdesk. You answer questions about
academic rules and regulations (attendance, grading, CGPA, exams, credits, degree requirements, minors,
specialisations), academic programmes, curricula and course contents, and academic calendar dates.
Procedure: call search_academic_documents with a SHORT keyword query (e.g. "maximum duration B.Tech",
"grade points letter grade", "make-up examination application"). Read every returned passage carefully - tables
are flattened into lines of text. If the answer is not in them, you MUST search a second time with different
keywords before giving up. Then answer from the returned passages only.
""" + GROUNDING_RULES

SCHEDULE_INSTRUCTION = """You are the Schedule Agent of the IIT Jodhpur Academic Helpdesk. You answer questions about
courses offered (floated) this semester, their slots, class timings, classrooms, credits and instructors,
and counts of courses offered by a department.
Tools:
- lookup_course: details (slot, instructor, credits...) of one course by code or title.
- get_slot_timing: days and times of a slot. When asked about a course's slot, also give its timings.
- list_offered_courses: list/COUNT courses filtered by department, level (e.g. 400) and course_type (e.g. "elective").
  For "how many" questions report the `count` field and list the course codes.
- search_academic_documents: academic calendar dates (semester start, exams, holidays).
""" + GROUNDING_RULES

EMAIL_INSTRUCTION = """You are the Email Agent of the IIT Jodhpur Academic Helpdesk. You help students write email
drafts to course instructors, e.g. to apply for (sick) leave or to request a make-up exam, and you can tell
students an instructor's email ID.
Procedure: call draft_email with the course, request_type ("leave", "sick_leave", "makeup_exam" or "other"),
and any reason, number of days, start date, name or roll number the student gave (leave unknown fields empty).
The tool looks up the instructor's email itself. Then show the complete draft to the student, say that it has
been saved and NOT sent, and cite the source. For only a contact question use get_instructor_contact.
""" + GROUNDING_RULES

ORCHESTRATOR_INSTRUCTION = f"""You are the orchestrator of the IIT Jodhpur Academic Helpdesk. You do NOT answer
questions yourself. Route the user's latest message by calling transfer_to_agent:
- policy_agent  : academic rules & regulations, attendance, grading, CGPA, exams, credits needed for a degree,
                  programmes, minors, curriculum and course contents/syllabus, academic calendar dates.
- schedule_agent: slot or timing of a course, timetable, courses offered/floated this semester, how many courses
                  a department offers, who teaches a course, classroom.
- email_agent   : ONLY when the user asks to write/draft an email to an instructor, or asks for an instructor's
                  email ID. Questions about the RULES for leave or make-up exams (deadlines, eligibility,
                  whom to apply to) go to policy_agent.
If the question is NOT about IIT Jodhpur academics (e.g. dining, food, hostel, transport, travel, directions,
sports, weather, fees payment portals, general knowledge), call log_unanswered_question(question, reason) and
then reply exactly: "{REFUSAL}"
"""

SINGLE_INSTRUCTION = """You are the IIT Jodhpur Academic Helpdesk agent. You answer questions about academic rules and
regulations, programmes, curricula and course contents, the academic calendar, course slots / timetable /
offerings this semester, and you draft emails from students to course instructors.
Tool guide:
- Rules, regulations, credits, programmes, course contents, calendar -> search_academic_documents with a SHORT
  keyword query; if the answer is not in the passages, search again with different keywords before giving up.
- Slot / instructor / details of a course -> lookup_course (then get_slot_timing for the timings).
- How many / which courses are offered this semester -> list_offered_courses (report its `count`).
- Email to an instructor (leave, sick leave, make-up exam) -> draft_email, then show the full draft and say it
  was saved and not sent. Instructor email ID -> get_instructor_contact.
- Anything not about IIT Jodhpur academics (dining, hostel, transport, travel, general knowledge) -> do not
  answer; call log_unanswered_question and give the refusal below.
""" + GROUNDING_RULES


def make_model(model_name=None):
    name = model_name or config.CHAT_MODEL
    if "/" in name:
        # Hosted provider via LiteLLM, e.g. "openrouter/qwen/qwen3-8b" or "groq/llama-3.1-8b-instant".
        # The API key is read from the provider's env var (OPENROUTER_API_KEY, GROQ_API_KEY, ...).
        return LiteLlm(model=name)
    extra = {}
    if name.startswith("qwen3") and not config.THINKING:
        extra["reasoning_effort"] = "none"  # LiteLLM maps this to Ollama think=false (much faster)
    return LiteLlm(model=f"ollama_chat/{name}", api_base=config.OLLAMA_BASE, num_ctx=config.NUM_CTX, **extra)


def _gen_config():
    return types.GenerateContentConfig(temperature=config.TEMPERATURE)


def build_single_agent(model_name=None):
    return LlmAgent(
        name="helpdesk_agent", model=make_model(model_name), instruction=SINGLE_INSTRUCTION,
        description="Single-agent IIT Jodhpur academic helpdesk.",
        tools=[search_academic_documents, lookup_course, list_offered_courses, get_slot_timing,
               get_instructor_contact, draft_email, log_unanswered_question],
        generate_content_config=_gen_config(),
    )


def build_multi_agent(model_name=None):
    model = make_model(model_name)
    common = dict(model=model, generate_content_config=_gen_config(),
                  disallow_transfer_to_parent=True, disallow_transfer_to_peers=True)
    policy = LlmAgent(
        name="policy_agent", instruction=POLICY_INSTRUCTION,
        description="Answers questions on academic rules/regulations, credits, programmes, curriculum, course contents and academic calendar.",
        tools=[search_academic_documents, log_unanswered_question], **common)
    schedule = LlmAgent(
        name="schedule_agent", instruction=SCHEDULE_INSTRUCTION,
        description="Answers questions on course slots, timings, timetable, courses offered this semester and instructors.",
        tools=[lookup_course, get_slot_timing, list_offered_courses, search_academic_documents, log_unanswered_question],
        **common)
    email = LlmAgent(
        name="email_agent", instruction=EMAIL_INSTRUCTION,
        description="Looks up instructor contacts and drafts emails to instructors (leave, sick leave, make-up exam).",
        tools=[draft_email, get_instructor_contact, log_unanswered_question], **common)
    return LlmAgent(
        name="helpdesk_orchestrator", model=model, instruction=ORCHESTRATOR_INSTRUCTION,
        description="Routes academic helpdesk questions to the right specialist agent.",
        tools=[log_unanswered_question], sub_agents=[policy, schedule, email],
        generate_content_config=_gen_config(),
    )
