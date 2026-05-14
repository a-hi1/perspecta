# ADR-002: Dual-Layer RAG Pipeline

**Date:** 2026-05-15
**Status:** Accepted

## Context

Standard RAG (Retriever-Augmented Generation) only performs semantic similarity search. For PEA, we need to go beyond finding relevant content — we need to extract the user's genuine opinions, judgments, and reflections from that content. This is the core differentiator of the system.

## Decision

Implement a two-layer retrieval pipeline:

### Layer 1: Semantic Recall
- Embed query using bge-m3 (multilingual, 1024-dim)
- Search ChromaDB with cosine similarity
- Retrieve top-k chunks (default k=10)
- Filter by user_id for multi-tenant isolation

### Layer 2: Perspective Extraction
- Feed Layer 1 results to LLM with specialized prompt
- Extract 5 types of perspectives:
  - **Judgment**: User's evaluative opinions
  - **Reflection**: Lessons learned from experience
  - **Lesson**: Actionable takeaways
  - **Controversy**: Disagreements with mainstream views
  - **Summary**: Synthesized viewpoints
- Each extraction includes confidence score, source quotes, and reasoning
- Chunks without extractable perspectives are filtered out

### Quality Evaluation
- Retrieval relevance scoring (LLM-as-judge)
- Perspective quality scoring (genuine opinion vs generic fact)
- Hallucination detection (generated content vs source backing)

## Alternatives Considered

1. **Single-layer RAG with reranking** — Insufficient. Reranking improves relevance but doesn't extract perspectives.

2. **Dedicated opinion extraction model** — Too complex for MVP. LLM-based extraction is sufficient and more flexible.

3. **Three-layer RAG (add fact verification)** — Deferred to v0.2. Citation verification handles this partially.

## Impact

- PerspectiveExtractor is a required component in the retrieval pipeline
- All retrieved chunks must pass through Layer 2 before being used in content generation
- Evaluation metrics must be computed for every pipeline run in development mode
- Confidence threshold of 0.5 filters low-quality extractions
