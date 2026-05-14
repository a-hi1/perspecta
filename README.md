# Personal Experience Amplifier (PEA)

> AI-powered perspective discovery and content curation system

PEA helps users discover their genuine professional perspectives from their personal knowledge base and create authentic LinkedIn content. It is NOT an AI content generator — it's a **thinking amplifier**.

## Key Features

- **Dual-Layer RAG**: Semantic recall + opinion extraction from your documents
- **Multi-Agent Workflow**: 10-stage pipeline with explicit state management
- **Perspective Discovery**: Extracts your genuine judgments, reflections, and lessons
- **Human-in-the-Loop**: All content requires your review and approval
- **Source Traceability**: Every claim links back to your original documents
- **Style Learning**: Adapts to your writing style from historical posts

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Next.js    │────▶│   FastAPI    │────▶│   Workflow   │
│   Frontend   │◀────│   Backend    │◀────│   Engine     │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ ChromaDB │ │ SQLite   │ │   LLM    │
        │ Vectors  │ │ Metadata │ │ Provider │
        └──────────┘ └──────────┘ └──────────┘
```

### Agent Workflow

```
HotTopic → TopicFilter → KnowledgeRetriever → PerspectiveDiscovery
→ AnglePlanner → DraftGenerator → StyleAdapter → CitationVerifier
→ HumanReview → Export
```

## Quick Start (Windows)

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for ChromaDB)

### Step 1: Configure environment

```cmd
copy .env.example .env
```

Edit `.env` and set your LLM API key (choose one):
- `DEEPSEEK_API_KEY` — Recommended, cheapest
- `QWEN_API_KEY` — Alibaba Qwen
- `GLM_API_KEY` — Zhipu GLM
- `MOONSHOT_API_KEY` — Moonshot/Kimi

### Step 2: Install backend dependencies

```cmd
cd backend
pip install -e .
cd ..
```

### Step 3: Install frontend dependencies

```cmd
cd frontend
npm install
cd ..
```

### Step 4: Initialize database

```cmd
cd backend
python init_db.py
cd ..
```

### Step 5: Start ChromaDB

```cmd
docker run -d --name pea-chromadb -p 8100:8000 -v chroma_data:/chroma/chroma chromadb/chroma:latest
```

### Step 6: Start backend

```cmd
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 7: Start frontend (new terminal)

```cmd
cd frontend
npm run dev
```

### Step 8: Open

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| ChromaDB | http://localhost:8100 |

## Quick Start (Docker)

```bash
docker-compose up -d
```

## Quick Start (One-Click)

```cmd
start.bat
```

## Usage Flow

1. **Upload Documents** — Go to Knowledge Base, upload your PDF/MD/TXT files
2. **Start Workflow** — Go to Dashboard, click "Start" (optionally enter a topic)
3. **Wait** — The agent pipeline runs: discovers topics, retrieves knowledge, extracts perspectives, generates drafts
4. **Review** — Go to Review Queue, review the generated draft with source citations
5. **Approve/Reject** — Approve to export, or reject with feedback for revision
6. **Export** — Copy the final content for LinkedIn

## Project Structure

```
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── agents/          # Workflow nodes & engine
│   │   ├── api/             # API endpoints
│   │   ├── core/            # Config, exceptions
│   │   ├── db/              # Database session & base
│   │   ├── evaluation/      # RAG quality evaluation
│   │   ├── llm/             # LLM provider abstraction
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── observability/   # Logging & tracing
│   │   ├── retrieval/       # Dual-layer RAG pipeline
│   │   ├── schemas/         # Pydantic request/response
│   │   └── services/        # Prompt loader
│   ├── alembic/             # Database migrations
│   ├── init_db.py           # Database initialization
│   └── pyproject.toml
├── frontend/                 # Next.js frontend
│   └── src/
│       ├── app/             # Pages
│       ├── components/      # UI components
│       ├── hooks/           # React hooks
│       ├── lib/             # API client, utilities
│       └── types/           # TypeScript types
├── prompts/                  # Versioned prompt files
│   ├── system/              # System prompts
│   ├── agents/              # Agent prompts
│   └── templates/           # Content templates
├── docs/
│   └── adr/                 # Architecture Decision Records
├── docker-compose.yml
├── start.bat                # Windows one-click start
├── start.sh                 # Linux/Mac one-click start
└── .env.example
```

## LLM Providers

| Provider | Model | API Key | Base URL |
|----------|-------|---------|----------|
| DeepSeek | deepseek-chat | `DEEPSEEK_API_KEY` | api.deepseek.com |
| Qwen | qwen-plus | `QWEN_API_KEY` | dashscope.aliyuncs.com |
| GLM | glm-4 | `GLM_API_KEY` | open.bigmodel.cn |
| Moonshot | moonshot-v1 | `MOONSHOT_API_KEY` | api.moonshot.cn |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/documents/upload` | Upload document |
| GET | `/api/v1/documents/` | List documents |
| POST | `/api/v1/workflow/start` | Start content generation |
| GET | `/api/v1/workflow/{id}` | Get workflow state |
| POST | `/api/v1/workflow/{id}/approve` | Approve draft |
| POST | `/api/v1/workflow/{id}/reject` | Reject draft |
| GET | `/api/v1/perspectives/` | List perspectives |
| GET | `/api/v1/drafts/` | List drafts |
| GET | `/api/v1/topics/` | List hot topics |

## License

MIT
