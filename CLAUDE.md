# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Production-grade **Agentic RAG** system for Finance/Legal document intelligence. Core loop: **Router → Retriever → Answerer → Checker** (with self-correction) orchestrated by LangGraph. Multi-tenant with strict per-user data isolation.

---

## Monorepo Structure

```
/
├── backend/          # FastAPI (Python 3.11+)
├── frontend/         # React 19 + Vite + TypeScript
├── docker-compose.yml  # ParadeDB (pgvector + pg_search built-in) + Redis Stack + arq worker
└── .env
```

---

## Backend

### Virtual Environment & Package Management
- Use **`uv`** for all Python dependency management (not pip, not poetry).
- Always create and use a virtual environment inside `backend/`.
```bash
cd backend
uv venv                  # create .venv in backend/
source .venv/bin/activate  # activate (Linux/macOS)
# .venv\Scripts\activate   # activate (Windows)
uv sync                  # install all deps into .venv
uv add <package>         # add dependency
uv run uvicorn app.main:app --reload   # dev server
uv run pytest            # run all tests
uv run pytest tests/path/test_file.py::test_name  # single test
```
> **Note:** `uv run` automatically uses the project venv. The explicit activate is only needed if you run commands directly (e.g., `python`, `alembic`).

### Key Libraries
- `fastapi`, `sqlmodel`, `alembic`, `pydantic-settings` — API + ORM + migrations + config
- `langgraph`, `langchain-core`, `langchain-anthropic`, `langchain-openai` — agent orchestration + LLM providers (use `langchain-core` not full `langchain` to avoid unnecessary deps)
- `pgvector` — Python bindings for pgvector (SQLAlchemy/SQLModel vector column support)
- `redis[hiredis]` — semantic cache (VSS) + arq task queue backend
- `openai` — OpenAI API client for embeddings
- `cohere` — Cohere API client for reranking (replaces local `sentence-transformers`)
- `llama-parse` — LlamaParse API client for PDF/DOCX parsing
- `asyncpg` — async PostgreSQL driver (required by SQLAlchemy async)
- `arq` — async task queue (Redis-backed) for document ingestion jobs
- `tiktoken` — BPE token limit checks (lightweight)
- `python-jose[cryptography]` — JWT auth
- `passlib[bcrypt]` — password hashing for user registration/login
- `langchain-text-splitters` — Markdown-aware + recursive character chunking

> **Removed heavy libraries:**
> - ~~`sentence-transformers`~~ — pulls PyTorch + Hugging Face transformers (~2 GB+). Replaced by **Cohere Rerank API**.
> - ~~`bitsandbytes`~~ — GPU quantization, not needed (no local models).
> - ~~`rank_bm25`~~ — replaced by **pg_search** PostgreSQL extension (persistent BM25 in-database).

### Database Migrations
```bash
uv run alembic upgrade head       # apply migrations
uv run alembic revision --autogenerate -m "description"  # new migration
```

---

## Frontend

### Package Management
- Use **`pnpm`** (preferred) or `npm`.
```bash
pnpm install
pnpm dev          # Vite dev server
pnpm build        # production build
pnpm lint         # ESLint
pnpm type-check   # tsc --noEmit
```

### Key Libraries
- `@tanstack/react-router` — file-based routing (`src/routes/`)
- `@tanstack/react-query` — server state, data fetching, mutations
- `tailwindcss` + `shadcn/ui` — styling and component primitives
- React 19 (client-side SPA via Vite — no Server Components)

---

## Architecture

### Backend Layout (`backend/`)
```
app/
├── main.py               # FastAPI app, lifespan, router mounts
├── core/
│   ├── config.py         # Settings via pydantic-settings
│   ├── security.py       # JWT creation/verification
│   └── database.py       # SQLModel engine, session factory
├── models/               # SQLModel table definitions
│   ├── user.py
│   ├── knowledge_base.py
│   ├── document.py
│   ├── chunk.py          # chunk text + embedding vector + foreign keys
│   ├── conversation.py
│   └── message.py        # individual chat messages within a conversation
├── api/
│   ├── auth.py           # /auth/login, /auth/register
│   ├── knowledge_bases.py
│   ├── documents.py      # upload, ingest pipeline trigger
│   └── chat.py           # SSE streaming endpoint
├── agent/                # LangGraph pipeline
│   ├── graph.py          # StateGraph definition and compilation
│   ├── state.py          # AgentState TypedDict
│   ├── nodes/
│   │   ├── router.py     # intent classification (fast model)
│   │   ├── answerer.py   # grounded generation (pro model)
│   │   └── checker.py    # hallucination / sufficiency audit
│   └── tools/
│       └── hybrid_search.py  # pg_search BM25 + pgvector → RRF → Cohere reranker
├── services/
│   ├── embedding.py      # OpenAI Embeddings API client
│   ├── reranker.py       # Cohere Rerank API wrapper
│   ├── cache.py          # Redis semantic cache
│   └── ingestion.py      # LlamaParse API parsing, chunking, BPE guard
├── workers/
│   └── ingestion_worker.py  # arq worker for async document ingestion
└── db/
    └── migrations/       # Alembic migration scripts
```

### Frontend Layout (`frontend/src/`)
```
routes/
├── _auth/               # unauthenticated layout
│   ├── login.tsx
│   └── register.tsx
├── _app/                # authenticated layout (sidebar + chat)
│   ├── index.tsx        # KB selector / landing
│   ├── kb.$kbId/
│   │   └── chat.$conversationId.tsx
│   └── kb.new.tsx
components/
├── chat/
│   ├── ChatWindow.tsx
│   ├── MessageBubble.tsx
│   └── ThinkingStream.tsx   # renders SSE agent steps
├── knowledge-base/
│   ├── KBSelector.tsx
│   └── DocumentUpload.tsx
└── ui/                      # shadcn/ui re-exports
lib/
├── api.ts               # typed fetch client (wraps fetch with JWT header)
├── auth.ts              # token storage helpers
└── queryClient.ts       # TanStack Query client config
```

---

## LangGraph Agent Pipeline

The graph state (`AgentState`) carries: `messages`, `query`, `retrieved_chunks`, `answer`, `checker_feedback`, `iteration_count`, `kb_id`, `user_id`.

**Node flow:**
1. **Router** (fast/cheap model) — classifies intent: `factual_query` → call `hybrid_search` tool | `greeting` → direct reply.
2. **Retriever Tool** — hybrid search:
   - pg_search BM25 (lexical, in-database) + pgvector HNSW (semantic, cosine) → top 15 each
   - Reciprocal Rank Fusion (RRF) to merge ranked lists
   - Cohere Rerank API re-scores → top 5 chunks returned
3. **Answerer** (pro model) — generates grounded response citing retrieved chunks.
4. **Checker** (auditor prompt) — evaluates answer:
   - `hallucination` → loop back to Answerer with critique (max 3 iterations)
   - `insufficient_data` → loop back to Router with broadened query
   - `pass` → stream final answer to user, write to Redis semantic cache

**Conditional edges** use `iteration_count` guard to prevent infinite loops.

---

## Key Technical Decisions

### Embeddings (OpenAI API)
- Use **OpenAI `text-embedding-3-small`** (or `text-embedding-3-large`) via the `openai` Python client.
- Supports native `dimensions` parameter for Matryoshka-style truncation (e.g., 1536 → 512) for speed/cost tradeoff.
- pgvector HNSW index: `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`.

### BM25 Search (pg_search extension)
- Use **`pg_search`** PostgreSQL extension for persistent, in-database BM25 full-text search.
- No in-memory index — survives restarts, scales with PostgreSQL, and supports RLS natively.
- Create a BM25 index on the `chunks` table: `CALL paradedb.create_bm25_index(...)`.
- Hybrid queries combine pg_search BM25 scores with pgvector cosine similarity via RRF.

### Multi-Tenancy / Security
- **PostgreSQL RLS** must be enabled on `knowledge_bases`, `documents`, `chunks`, `conversations`, `messages` tables — every query must pass `user_id` via `SET app.current_user_id`.
- JWT middleware sets `app.current_user_id` at the start of every request via a FastAPI dependency.
- Never bypass RLS in application code.

### Semantic Cache (Redis + VSS)
- Uses **Redis Vector Similarity Search (redis-vss)** via the `RediSearch` module.
- On each query: embed the query via OpenAI → run vector similarity search against cached query embeddings in Redis (filtered by `kb_id`).
- Similarity threshold (e.g., cosine > 0.95): cache hit → skip the full LangGraph pipeline and return cached answer directly.
- Cache miss → run pipeline → store `{query_embedding, answer, kb_id}` in Redis with configurable TTL (default 1 hour).
- Requires Redis Stack (includes RediSearch + RedisJSON) → use `redis/redis-stack` Docker image.

### Docker Images
- **PostgreSQL**: use `paradedb/paradedb` image (ships with both `pgvector` and `pg_search` pre-installed). Do **not** use plain `postgres` or `pgvector/pgvector` — pg_search won't be available.
- **Redis**: use `redis/redis-stack` image (includes RediSearch for VSS + RedisJSON).

### Chunking Strategy (two-stage)
1. **Stage 1 — Markdown-aware split** (`MarkdownHeaderTextSplitter`):
   - LlamaParse outputs structured Markdown → split on headers (`#`, `##`, `###`) to produce semantic sections.
   - Each section retains its header hierarchy as metadata (e.g., `{"h1": "Contract Terms", "h2": "Termination"}`).
   - Tables and lists within a section are kept intact (not split mid-row).
2. **Stage 2 — Recursive character split** (`RecursiveCharacterTextSplitter`):
   - Any section exceeding ~400 tokens is further split using recursive character splitter (overlap 50 tokens).
   - Separators: `["\n\n", "\n", ". ", " "]` — prefers paragraph/sentence boundaries.
3. **BPE Token Guard** — before embedding, `tiktoken` verifies each chunk is ≤ 512 tokens. Over-limit chunks are re-split.
4. Log and alert if a document exceeds a configurable total token budget.

### SSE Streaming
- The `/api/chat/stream` endpoint uses FastAPI `StreamingResponse` with `text/event-stream`.
- Each LangGraph node emits a typed SSE event: `{"event": "thinking", "node": "router", "data": "..."}` or `{"event": "token", "data": "..."}` for answer tokens.
- Frontend `ThinkingStream` component consumes the SSE and renders agent steps in a collapsible panel.

### API-Only Inference (no local models)
- All LLM calls, embeddings, and reranking use **external API providers** (Anthropic for LLMs, OpenAI for embeddings, Cohere for reranking).
- No local model loading, no GPU requirements, no quantization (`bitsandbytes`, `sentence-transformers`, `torch` are **not** dependencies).
- Keep lightweight libraries like `tiktoken` for token counting.

---

## Environment Variables

All secrets live in `.env` (never committed). Key variables:
```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
SECRET_KEY=...          # JWT signing key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ANTHROPIC_API_KEY=...             # LLM calls (Claude)
OPENAI_API_KEY=...                # embeddings (text-embedding-3-small)
COHERE_API_KEY=...                # Cohere Rerank API
COHERE_RERANK_MODEL=rerank-v3.5   # Cohere reranker model
LLAMA_CLOUD_API_KEY=...           # LlamaParse document parsing
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536         # or truncated (e.g., 512)
```

---

## Data Flow: Document Ingestion

1. User uploads PDF/DOCX via `POST /api/knowledge-bases/{kb_id}/documents`.
2. API endpoint saves file metadata to DB, enqueues an **arq** job for async processing.
3. **arq worker** picks up the job:
   a. **LlamaParse API** parses PDF/DOCX → structured Markdown/text.
   b. Two-stage chunking: `MarkdownHeaderTextSplitter` (split by headers) → `RecursiveCharacterTextSplitter` (~400 tokens, overlap 50) → BPE token guard via `tiktoken`.
   c. Each chunk embedded via **OpenAI Embeddings API** → stored in `chunks` table with `embedding vector(1536)` and `user_id` (for RLS).
   d. pg_search BM25 index auto-updates (in-database, no rebuild needed).
4. Job status tracked in DB; frontend polls or uses WebSocket for completion notification.

## Data Flow: Chat Query

1. `POST /api/chat/{conversation_id}/stream` → validates JWT → sets RLS context.
2. Semantic cache lookup in Redis → hit: stream cached answer.
3. Cache miss → invoke `graph.astream(state)` → SSE-emit each node event.
4. Final answer saved to `conversations` table + Redis cache.

---

## CI/CD

### GitHub Actions
- **CI** (`.github/workflows/ci.yml`): runs on every push/PR — pytest with coverage on backend, pnpm lint + type-check + test on frontend, Docker image build.
- **CD** (`.github/workflows/cd.yml`): on push to `main` — builds and pushes backend/frontend images to GHCR (`ghcr.io`).

### Traefik Reverse Proxy
- Config in `traefik/traefik.yml` — Traefik v3.3 with Docker provider, ACME Let's Encrypt, HTTP→HTTPS redirect.
- Dynamic middleware in `traefik/dynamic/middlewares.yml` — security headers (CSP, X-Frame-Options), rate limiting (100 req/s general, 30 req/s API, 5 req/min auth).

---

## Monitoring & Evaluation

### Phoenix (OpenTelemetry tracing)
- `arizephoenix/phoenix:latest` service in `docker-compose.yml` (port 6006, routed via Traefik at `/phoenix`).
- Backend/worker export traces via `PHOENIX_COLLECTOR_ENDPOINT=http://phoenix:4317`.
- Dependencies: `openinference-instrumentation-langchain`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-grpc`.

### Ragas (RAG evaluation)
- `ragas>=0.4.3` in backend dependencies for offline evaluation of retrieval and generation quality.

---

## Skills Module

- **Model**: `app/models/skill.py` — SQLModel table for user-uploaded `.md` skill files (max 100 KB, per-user).
- **API**: `app/api/skills.py` — `POST /api/skills/` to upload `.md` skills.

---

## Testing

- **Framework**: `pytest` + `pytest-asyncio` + `httpx` (async test client) + `pytest-cov`.
- **Location**: `backend/tests/` — mirrors `app/` structure (`agent/`, `api/`, `core/`, `services/`).
- **Config**: `pyproject.toml` → `testpaths = ["tests"]`, `asyncio_mode = "auto"`.
```bash
uv run pytest                                          # all tests
uv run pytest tests/api/test_skills.py                 # single file
uv run pytest tests/api/test_skills.py::test_name      # single test
uv run pytest --cov=app --cov-report=term-missing      # with coverage
```

---

## Practical Tips

### Batch-staging bug fixes
When fixing multiple bugs in one session, stage and commit them in logical batches rather than one giant commit or one-per-file:

```bash
# 1. Fix a group of related bugs (e.g., all security fixes), then stage together:
git add backend/app/core/security.py backend/app/api/auth.py backend/app/main.py
git commit -m "fix(security): add CSP headers, rate-limit auth, enforce password policy"

# 2. Fix the next logical group (e.g., agent pipeline bugs), stage together:
git add backend/app/agent/nodes/router.py backend/app/agent/nodes/checker.py backend/app/services/cache.py
git commit -m "fix: harden agent pipeline logic and add cache invalidation on KB changes"
```

**Rules of thumb:**
- Group by **theme** (security, pipeline logic, data integrity) — not by file type or directory.
- Each commit should be independently meaningful: if you `git revert` one commit, it undoes one coherent fix — not half of two unrelated fixes.
- Use `git add -p` (patch mode) when a single file contains changes for multiple bug fixes — stage only the hunks belonging to the current batch.
- Write the commit message **before** staging so you know exactly which files belong to that theme.
- Run tests (`uv run pytest`) between batch commits to confirm each batch is green on its own.
