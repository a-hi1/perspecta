# ADR-001: System Architecture

**Date:** 2026-05-15
**Status:** Accepted

## Context

We are building a Personal Experience Amplifier (PEA) — an AI Agent system that helps users discover their genuine professional perspectives from their knowledge base and create authentic LinkedIn content. The system must NOT be a generic AI content generator; it must be a "thinking amplifier" that surfaces real user viewpoints.

## Decision

### Architecture: Monorepo with FastAPI + Next.js + LangGraph

**Backend (FastAPI + Python 3.11+)**
- RESTful API for all operations
- SQLAlchemy async ORM with SQLite (MVP) / PostgreSQL (production)
- ChromaDB for vector storage
- LangGraph for agent workflow orchestration

**Frontend (Next.js 15 + TypeScript)**
- 5 core pages: Dashboard, Knowledge Base, Perspectives, Draft Studio, Review Queue
- shadcn/ui + Tailwind for UI
- Real-time agent status display

**Agent Workflow: LangGraph State Machine**
- 10 nodes: HotTopic → TopicFilter → KnowledgeRetriever → PerspectiveDiscovery → AnglePlanner → DraftGenerator → StyleAdapter → CitationVerifier → HumanReview → Export
- Explicit state transitions with validation
- Human-in-the-loop at HumanReview node
- Full tracing and observability

**RAG Pipeline: Dual-Layer**
- Layer 1: Semantic recall via bge-m3 embeddings + ChromaDB cosine similarity
- Layer 2: Perspective extraction via LLM analysis of retrieved chunks

**LLM Abstraction: Provider-Agnostic**
- BaseLLMProvider interface
- Supports DeepSeek, Qwen, GLM, Moonshot via OpenAI-compatible API
- Factory pattern for provider selection

## Alternatives Considered

1. **LangChain high-level abstractions** — Rejected due to excessive abstraction and debugging difficulty. Using LangGraph directly for state machine control.

2. **Pinecone/Weaviate for vector DB** — Rejected for MVP simplicity. ChromaDB can run locally without external service.

3. **OpenAI as primary LLM** — Rejected to avoid vendor lock-in and support Chinese LLM providers (DeepSeek, Qwen, GLM).

4. **Next.js API routes as backend** — Rejected. Python backend is necessary for ML/AI libraries (sentence-transformers, PyMuPDF, LangGraph).

## Impact

- All agent nodes must implement the defined input/output schema
- All prompts must be versioned in /prompts/ directory
- All RAG results must pass through both layers
- Human review is mandatory before any content export
- Every generated claim must have source traceability
