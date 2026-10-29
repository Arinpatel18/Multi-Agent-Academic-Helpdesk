"""Central configuration. Every value can be overridden with an environment variable."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DOCS_DIR = ROOT / "data" / "documents"
STRUCTURED_DIR = ROOT / "data" / "structured"
VECTORSTORE_DIR = ROOT / "vectorstore"
CHUNKS_FILE = VECTORSTORE_DIR / "chunks.jsonl"
LOG_DIR = Path(os.getenv("HELPDESK_LOG_DIR", ROOT / "logs"))
UNANSWERED_LOG = LOG_DIR / "unanswered_questions.jsonl"
DRAFTS_DIR = Path(os.getenv("HELPDESK_DRAFTS_DIR", ROOT / "outputs" / "email_drafts"))

COURSES_CSV = STRUCTURED_DIR / "course_offerings_AY2026-27_Sem1.csv"
SLOTS_CSV = STRUCTURED_DIR / "slot_timetable.csv"
FACULTY_CSV = STRUCTURED_DIR / "faculty_directory.csv"

OLLAMA_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
# Default = the 4B model used for all reported results (runs on an 8 GB M1 Mac).
# On a 16 GB machine an 8B model can be used instead: HELPDESK_MODEL=qwen3:8b
CHAT_MODEL = os.getenv("HELPDESK_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
EMBED_MODEL = os.getenv("HELPDESK_EMBED_MODEL", "nomic-embed-text")
TEMPERATURE = float(os.getenv("HELPDESK_TEMPERATURE", "0.2"))
NUM_CTX = int(os.getenv("HELPDESK_NUM_CTX", "8192"))
THINKING = os.getenv("HELPDESK_THINKING", "0") == "1"   # qwen3 "thinking" mode; off = several times faster

COLLECTION = "iitj_academic_docs"
CHUNK_SIZE = 1200          # characters
CHUNK_OVERLAP = 200
TOP_K = 6
CURRENT_SEMESTER = "AY 2026-27, Semester I (July-November 2026)"
