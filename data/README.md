# Document collection (27 documents)

## A. Real IIT Jodhpur documents — `data/documents/` (24, indexed in the vector store)

All downloaded from the public IIT Jodhpur website (Office of Academics pages) on 29 Oct 2026.
Base URLs: `https://www.iitj.ac.in/PageImages/Gallery/…`, `https://intranet.iitj.ac.in/acad_website/…`.

| # | File | What it is |
|---|---|---|
| 01 | `01_Academic_Regulations_Part1_2019.pdf` | UG+PG Academic Rules & Regulations (students enrolled from July 2019): attendance, grading, make-up exams, B.Tech credit structure, minors, max. duration |
| 04 | `04_Notification_26102020_A.pdf` | Office of Academics notification amending the regulations (26.10.2020) |
| 07 | `07_PG_Regulations_2022_onwards.pdf` | PG Rules & Regulations for students enrolled from July 2022 |
| 08 | `08_Circular_OA_2022-01-20.pdf` | Circular: regulations for IIT Jodhpur–AIIMS Jodhpur joint programmes |
| 09 | `09_Circular_2024-04-17.pdf` | Circular: Rules & Regulations for M.S. by Research programmes |
| 12 | `12_Academic_Calendar_AY2026-27.pdf` | Academic calendar AY 2026-27 (current year) |
| 13 | `13_Academic_Calendar_AY2025-26.pdf` | Academic calendar AY 2025-26 |
| 14 | `14_Academic_Calendar_Summer_2026.pdf` | Academic calendar, Summer Term 2026 |
| 15 | `15_BTech_CSE_Curriculum.pdf` | B.Tech CSE curriculum and course contents |
| 16 | `16_BTech_AIDS_Curriculum.pdf` | B.Tech AI & Data Science curriculum |
| 17 | `17_BTech_EE_Curriculum.pdf` | B.Tech EE curriculum |
| 18 | `18_Institute_Common_Courses.pdf` | Institute-wide common courses and contents |
| 19 | `19_Minor_and_Specialization.pdf` | Minor / department / interdisciplinary specialisation structure |
| 20 | `20_MTech_CSE_Curriculum.pdf` | M.Tech CSE course booklet |
| 21 | `21_BTech_ME_Curriculum.pdf` | B.Tech ME curriculum |
| 22 | `22_BTech_BB_Curriculum.pdf` | B.Tech Bioscience & Bioengineering curriculum |
| 23 | `23_HSS_Concept_Note_2021.pdf` | HSS department concept note and HSS course contents |
| 24 | `24_BTech_Civil_Curriculum.pdf` | B.Tech Civil curriculum |
| 25 | `25_PG_Computer_Science_Courses_2019.pdf` | PG course booklet — Computer Science |
| 26 | `26_PG_HSS_Courses_2019.pdf` | PG course booklet — HSS |
| 29 | `29_Slot_System_FirstYear_2023.xlsx` | First-year slot system / timetable (faculty names & emails **replaced with dummy values**) |
| 30 | `30_UG_Registration_Guidelines.md` | UG registration guidelines web page (HSS elective basket) |
| 31 | `31_List_of_Academic_Programs.md` | List of academic programmes AY 2026-27 web page |
| 32 | `32_Specialization_Minor_DualDegree.md` | Specialisation / minor / dual degree web page |

Removed during collection: exact duplicates (regulations parts 2-3, two copies of the 2020 notification),
two scanned circulars without a text layer, a corrupt download, and a first-year section allocation list
(student roll numbers — personal data, no helpdesk value).

## B. Structured data — `data/structured/` (3, used by the CSV lookup tools)

The current-semester course offering list, timetable and faculty email IDs are on the IITJ intranet and
are not public, so these files are **reconstructed samples** in the real IITJ format:

| File | Content |
|---|---|
| `course_offerings_AY2026-27_Sem1.csv` | 38 courses: code, title, department, level, credits, L-T-P, type, slot, instructor, room. Course titles and HSS course codes are taken from the real curricula above; other codes are illustrative. |
| `slot_timetable.csv` | Slot → days and timings (pattern follows the real IITJ slot system in doc 29). |
| `faculty_directory.csv` | Instructor → designation, department, email, office. **All names and emails are dummy values** (`@iitj-dummy.ac.in`). |

To use real data, replace these three CSVs with the official versions (same column names). No code change
is needed. To add documents, drop PDF/MD/XLSX files into `data/documents/` and re-run
`python -m helpdesk.ingest --reset`.
