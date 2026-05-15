# CLAUDE.md — Perspecta Project Context

## Project Overview

**Perspecta** (formerly "PEA") is an AI-powered perspective discovery and content curation system. It helps users discover genuine professional perspectives from their personal knowledge base and create authentic LinkedIn content.

**Core principle**: This is NOT an AI content generator. It is a "thinking amplifier" that surfaces real user viewpoints with full source traceability.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11+ |
| Frontend | Next.js 15 + TypeScript + Tailwind CSS |
| Database | SQLite (SQLAlchemy async) + ChromaDB (vectors) |
| Embedding | BAAI/bge-m3 via sentence-transformers |
| LLM | DeepSeek / Qwen / GLM / Moonshot via OpenAI-compatible API |
| Workflow | Custom async state machine (not LangGraph) |

## Architecture

```
Frontend (Next.js:3000) → Backend (FastAPI:8000) → Workflow Engine → LLM Provider
                                              ↓
                            ChromaDB:8100  +  SQLite (pea.db)
```

### Agent Workflow Pipeline

```
HotTopic → TopicFilter → KnowledgeRetriever → PerspectiveDiscovery
→ AnglePlanner → DraftGenerator → StyleAdapter → CitationVerifier
→ HumanReview → Export
```

- Each node is an async class in `backend/app/agents/nodes/`
- State flows through `WorkflowState` dataclass
- `HumanReview` pauses for external approval (human-in-the-loop)
- Rejection loops back to `DraftGenerator` with feedback

## Directory Structure

```
perspecta/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── nodes/           # 10 agent node implementations
│   │   │   ├── state/           # WorkflowState dataclass + transitions
│   │   │   └── workflow.py      # Workflow engine (orchestrates nodes)
│   │   ├── api/v1/endpoints/    # FastAPI route handlers
│   │   ├── core/                # config.py (Settings), exceptions.py
│   │   ├── db/                  # SQLAlchemy base, session
│   │   ├── evaluation/          # RAG quality evaluator
│   │   ├── llm/                 # LLM abstraction: base.py, providers.py, factory.py
│   │   ├── models/              # SQLAlchemy ORM models (9 tables)
│   │   ├── observability/       # logger.py (JSON-lines), tracer.py (workflow replay)
│   │   ├── retrieval/           # Dual-layer RAG: parser, chunker, embedder, vector_store, retriever, perspective_extractor
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── services/            # prompt_loader.py
│   ├── alembic/                 # Database migrations
│   ├── init_db.py               # Table creation script
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── app/                 # Next.js pages (dashboard, knowledge-base, perspectives, draft-studio, review-queue)
│       ├── components/          # UI components (agent-status, sidebar)
│       ├── hooks/               # useWorkflow hook
│       ├── lib/                 # api.ts (API client), utils.ts
│       └── types/               # TypeScript type definitions
├── prompts/
│   ├── system/base.md           # Base system prompt for all agents
│   ├── agents/                  # Per-agent prompts (versioned with YAML frontmatter)
│   └── templates/               # Post templates (professional, story, controversial)
├── docs/adr/                    # Architecture Decision Records
├── docker-compose.yml
├── start.bat / start.sh         # One-click startup scripts
└── .env.example
```

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/core/config.py` | All settings via pydantic-settings, loaded from `.env` |
| `backend/app/llm/base.py` | `BaseLLMProvider` abstract class — all LLM calls go through here |
| `backend/app/llm/factory.py` | `create_llm_provider()` — factory for provider selection |
| `backend/app/agents/state/workflow_state.py` | `WorkflowState` dataclass + `VALID_TRANSITIONS` + all data types |
| `backend/app/agents/workflow.py` | `ContentGenerationWorkflow` — main orchestrator |
| `backend/app/retrieval/retriever.py` | `DualLayerRetriever` — Layer 1 semantic + Layer 2 perspective extraction |
| `backend/app/services/prompt_loader.py` | Loads versioned prompts from `/prompts/` directory |
| `backend/app/main.py` | FastAPI app creation and CORS setup |
| `frontend/src/lib/api.ts` | Frontend API client (all backend calls) |

## Database Models

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | users | User accounts |
| `Document` | documents | Uploaded knowledge documents |
| `DocumentChunk` | document_chunks | Text chunks with embedding references |
| `HotTopic` | hot_topics | Discovered trending topics |
| `Perspective` | perspectives | Extracted user viewpoints |
| `Draft` | drafts | Generated LinkedIn post drafts |
| `DraftVersion` | draft_versions | Version history for drafts |
| `StyleProfile` | style_profiles | Learned writing style |
| `Citation` | citations | Source traceability links |
| `AgentRunLog` | agent_run_logs | Execution logs for observability |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/documents/upload` | Upload document (PDF/MD/TXT) |
| `GET` | `/api/v1/documents/` | List documents |
| `GET` | `/api/v1/documents/{id}/chunks` | Get document chunks |
| `DELETE` | `/api/v1/documents/{id}` | Delete document |
| `POST` | `/api/v1/workflow/start` | Start content generation workflow |
| `GET` | `/api/v1/workflow/{id}` | Get workflow state |
| `POST` | `/api/v1/workflow/{id}/approve` | Approve draft (human-in-the-loop) |
| `POST` | `/api/v1/workflow/{id}/reject` | Reject draft with feedback |
| `GET` | `/api/v1/workflow/{id}/diagram` | Get Mermaid workflow diagram |
| `GET` | `/api/v1/perspectives/` | List perspectives |
| `GET` | `/api/v1/drafts/` | List drafts |
| `PUT` | `/api/v1/drafts/{id}` | Update draft content |
| `GET` | `/api/v1/topics/` | List hot topics |

## Conventions

### Python
- Python 3.11+, fully typed with `mypy`-compatible annotations
- Async everywhere (`async def`, `AsyncSession`, `AsyncOpenAI`)
- Pydantic v2 for all request/response schemas
- SQLAlchemy 2.0 async ORM with `Mapped[]` column syntax
- No `print()` — use `AgentLogAdapter` for structured JSON-lines logging

### TypeScript
- Next.js 15 App Router (`src/app/`)
- `cn()` utility (clsx + tailwind-merge) for className merging
- API client in `src/lib/api.ts` with typed responses
- Components in `src/components/`, hooks in `src/hooks/`

### Prompts
- All prompts stored in `/prompts/` with YAML frontmatter (version, description, changelog)
- Loaded via `PromptLoader` service — never hardcoded in business code
- Modify prompts → update version number + changelog

### Agent Nodes
- Each node is a class with `async def execute(self, state: WorkflowState) -> WorkflowState`
- Must call `state.transition_to(AgentNode.X)` at the end
- Must log via `AgentLogAdapter` with input/output summary, latency, tokens
- On failure: call `state.mark_failed(error_message)` and return

### State Transitions
- Defined in `VALID_TRANSITIONS` dict in `workflow_state.py`
- Invalid transitions raise `WorkflowStateError`
- `HumanReview` is the only node that pauses (`WAITING_APPROVAL`)

## Running

```bash
# Backend
cd backend && pip install -e . && python init_db.py && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# ChromaDB
docker run -d -p 8100:8000 chromadb/chroma:latest
```

Set `DEEPSEEK_API_KEY` in `.env` (or `QWEN_API_KEY` / `GLM_API_KEY` / `MOONSHOT_API_KEY`).

## Anti-Patterns (Do NOT)

- Do not hardcode prompts in agent nodes — use `PromptLoader`
- Do not skip `state.transition_to()` — state transitions are validated
- Do not auto-publish content — `HumanReview` approval is mandatory
- Do not add LangChain high-level abstractions — keep the stack lean
- Do not generate content without source citations — every claim needs traceability
- Do not create `utils_v2.py` or duplicate modules — follow the existing directory structure
- Do not add microservices / k8s / message queues — this is a monolith by design
