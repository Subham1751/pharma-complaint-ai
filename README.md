# Pharma Complaint AI — AIVOA Copilot

An AI-powered Customer Complaint Management System for pharmaceutical manufacturing,
built for the AIVOA Round 1 AI Product Engineer (Intern) assessment.

A chat-based **AIVOA Copilot** on the right drives the **Log Customer Complaint** form
and its **AI Risk Assessment** on the left — via natural language, PDF upload, or both.
This mirrors the reference demo: you never fill the form by hand, you tell the copilot
what happened (or hand it a document) and it does the data entry and risk reasoning.

## The three required AI tools

| Tool                    | Trigger                                    | What it does                                                                                                                                                                                 |
| ----------------------- | ------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Log Complaint**       | A fresh message, no active complaint       | Extracts structured fields from a natural-language description and generates the initial risk assessment (severity, root cause, CAPA, completeness).                                         |
| **Edit Complaint**      | A follow-up message on an active complaint | Parses the correction/update ("the batch number is actually BMX240602"), changes _only_ those fields, preserves everything else, and re-runs the risk assessment against the updated record. |
| **Document Extraction** | A PDF is attached                          | Extracts text from the PDF and runs the same structured extraction + risk assessment as the Log tool, seeding a new complaint from the document.                                             |

All three tools funnel into one shared LangGraph pipeline (completeness → risk
classification → root cause → CAPA → duplicate check → summary), so the AI Risk
Assessment panel is always in sync with whatever is currently in the form — including
right after an edit.

## Why routing is deterministic, not model-driven tool-calling

The copilot endpoint decides which tool to run from the **shape of the request**, not
by asking the LLM to choose a tool:

- a PDF is attached → **Document Extraction**
- no PDF, but there's an active `complaint_id` → **Edit Complaint**
- no PDF, no active complaint → **Log Complaint**

This was a deliberate tradeoff: Groq's `gemma2-9b-it` is fast and cheap but not
reliable at function-calling, and a live demo needs the _right_ tool to fire every
time. Keeping tool selection deterministic means it always works, while the actual
reasoning inside each tool (what to extract, what changed, how risky it is) is still
fully LLM-driven. A natural next step for a production version would be to swap this
for real LLM tool-calling using `llama-3.3-70b-versatile` on Groq, which does support
it — but that trades a bit of reliability for a more general agent.

## Architecture

```
 React (Redux Toolkit)                     FastAPI                        LangGraph + Groq
┌───────────────────────┐        HTTP     ┌───────────────────────┐      ┌──────────────────────────┐
│ LogComplaintForm       │ ◀────────────── │ POST /copilot/message  │ ──▶ │ route_by_mode (deterministic)│
│  (left: form + risk)   │                 │  (message?, file?,     │     │   ├─ log_complaint          │
│                        │                 │   complaint_id?)        │     │   ├─ edit_complaint         │
│ CopilotChat             │ ──────────────▶ │                        │     │   └─ document_extraction    │
│  (right: chat + upload)│                 │ GET  /complaints/       │     │            │                 │
│                        │                 │ GET  /complaints/{id}  │     │            v                 │
│ ComplaintLogTable       │ ◀────────────── │                        │     │  completeness_check          │
└───────────────────────┘                 └───────────┬────────────┘     │  risk_classification         │
                                                        │                  │  root_cause_recommendation   │
                                                        ▼                  │  capa_recommendation          │
                                               PostgreSQL (complaints)     │  duplicate_detection          │
                                                                            │  summarize                    │
                                                                            │  generate_reply (chat bubble) │
                                                                            └──────────────────────────┘
```

**End-to-end flow (log → edit → resume):**

1. User types a complaint description (or attaches a PDF) in `CopilotChat.jsx`.
2. Redux thunk `sendMessage` posts to `POST /api/v1/copilot/message` as multipart form
   data (`message`, optional `file`, optional `complaint_id` if a complaint is already active).
3. `app/api/copilot.py` determines the mode, extracts PDF text if needed, gathers recent
   complaints for duplicate-check context, and calls `copilot_graph.invoke(...)`.
4. The LangGraph workflow (`app/agents/graph.py`) routes to the right tool, then runs the
   shared risk-assessment pipeline (`app/agents/nodes.py`), each node calling Groq
   (`gemma2-9b-it`, falling back to `llama-3.3-70b-versatile` on error/bad JSON).
5. The endpoint upserts the complaint row (creates new, or merges onto the existing one
   for edits) and appends both chat turns to `chat_history`.
6. The response (`{complaint, assistant_reply, tool_used, changed_fields}`) updates
   Redux: `formState` drives `LogComplaintForm.jsx`, `assistant_reply` becomes a new chat
   bubble in `CopilotChat.jsx`, and `changed_fields` highlights whatever the form fields
   the last turn touched.
7. Sending another message on the same thread (no file) routes to **Edit Complaint**
   automatically, since `complaint_id` is now set in Redux state.
8. Clicking a row in `ComplaintLogTable` calls `resumeComplaintThread`, reloading that
   complaint's full field state + chat history to continue editing it.

## Tech stack

| Layer            | Choice                                                                |
| ---------------- | --------------------------------------------------------------------- |
| Frontend         | React 18 + Redux Toolkit + Vite                                       |
| Backend          | Python + FastAPI                                                      |
| AI orchestration | LangGraph (conditional routing across 3 tools)                        |
| LLM              | Groq — `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (fallback) |
| Database         | PostgreSQL (SQLAlchemy ORM)                                           |
| Font             | Google Inter                                                          |

## Project structure

```
pharma-complaint-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, startup
│   │   ├── config.py            # env-based settings
│   │   ├── database.py          # SQLAlchemy engine/session
│   │   ├── models.py            # Complaint ORM model (form fields + AI fields + chat_history)
│   │   ├── schemas.py           # Pydantic request/response models
│   │   ├── api/
│   │   │   ├── copilot.py       # POST /copilot/message — the 3-tool entry point
│   │   │   └── complaints.py    # GET list/detail, for the log table
│   │   ├── agents/
│   │   │   ├── llm.py           # Groq client wrapper (JSON mode + fallback)
│   │   │   ├── nodes.py         # the 3 tools + shared risk-assessment pipeline
│   │   │   └── graph.py         # LangGraph StateGraph with conditional routing
│   │   └── utils/document_parser.py  # PDF text extraction
│   ├── sample_data/             # example complaint text for demoing
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LogComplaintForm.jsx   # left pane: form + risk assessment
│   │   │   ├── CopilotChat.jsx        # right pane: chat + file attach
│   │   │   ├── ComplaintLogTable.jsx  # bottom: past complaints, click to resume
│   │   │   ├── RiskBadge.jsx
│   │   │   └── CompletenessGauge.jsx
│   │   ├── store/complaintSlice.js    # chat state, form state, thunks
│   │   ├── api/complaintApi.js        # axios client
│   │   └── styles/index.css
│   └── package.json
└── docker-compose.yml            # local Postgres
```

## Setup

### 1. Database

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and paste your Groq API key from https://console.groq.com
uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`. Health check at `http://localhost:8000/health`.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

App at `http://localhost:3000`.

## Demoing it

1. Click a suggestion chip (or type your own complaint description) → **Log Complaint**
   fires, the form and risk assessment populate.
2. Type a correction, e.g. _"actually the affected quantity is 48 capsules"_ →
   **Edit Complaint** fires; watch only that field update (highlighted) while everything
   else stays put.
3. Click **+ New complaint**, then attach a PDF (see `backend/sample_data/`) →
   **Document Extraction** fires.
4. Log a second complaint about the same product/issue → duplicate detection should flag it.
5. Click a row in the Complaint Log to reopen that thread and keep editing it.

## AI features implemented

- **Log Complaint Tool** — natural-language → structured form fields + initial risk assessment.
- **Edit Complaint Tool** — natural-language corrections, diffed and merged, preserving
  everything untouched, with the risk assessment recomputed.
- **Document Extraction Tool** — PDF/email text → structured fields + risk assessment.
- **Complaint Completeness Checker** — flags missing required fields, scored 0–100%.
- **AI Risk Classification** — Critical / Major / Minor, with justification.
- **Root Cause Recommendation** — 2–4 investigation-starting hypotheses.
- **CAPA Recommendation** — corrective + preventive action suggestions.
- **Duplicate Complaint Detection** — compares against recent complaints for the same issue.
- **Complaint Summary** — 2–3 sentence QA-reviewer-facing summary.

## Notes on scope

- OCR/document parsing is intentionally simple (`pypdf` text-layer extraction only, no
  scanned-image OCR), per the assignment's stated scope.
- Tool routing is deterministic by request shape rather than LLM-driven function calling
  — see the rationale above.
- `Base.metadata.create_all()` is used for schema creation instead of Alembic migrations,
  since this is a scoped assessment project rather than a long-lived production service.
- Chat history is stored as a JSON column on the complaint row (one thread per complaint)
  rather than a separate table, since that's all this demo's scope needs.
