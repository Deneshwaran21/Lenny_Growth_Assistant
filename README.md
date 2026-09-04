# The Lenny Growth Assistant

A full-stack, AI-powered conversational assistant that answers product and
growth questions grounded in Lenny's Podcast transcripts, writes Ship 30 for
30–style essays, and generates Markdown/HTML artifacts rendered in an
in-app, sandboxed Artifact Viewer.

Built for the Forward Deployed Engineer take-home assessment. See `PRD.md`,
`design.md`, and `architecture.md` for the discovery brief, UI/UX
rationale, and system design respectively.

## Architecture at a glance

- **Backend**: FastAPI + async SQLAlchemy (Postgres)
- **Agent layer**: custom router → three skills (grounded Q&A, Ship 30/30
  essay, artifact generation) → provider-agnostic LLM client
- **Model toggle**: `anthropic` / `openai` / `ollama` via `.env`, with
  automatic fallback if the primary provider is unreachable
- **Retrieval**: TF-IDF over chunked transcripts (no external embedding
  service required to run the demo)
- **Frontend**: React + TypeScript (Vite), sandboxed-iframe Artifact Viewer
- **Deployment**: Docker Compose (Postgres + Ollama + backend + frontend)

Full diagrams and schema in `architecture.md`.

## Prerequisites

- Docker + Docker Compose (recommended path), **or**
- Python 3.11+, Node 20+, and a local Postgres instance for a manual run
- [Ollama](https://ollama.com) if running the local model outside Docker

## Quickstart (Docker Compose — recommended)

```bash
cp .env.example .env
docker compose up --build
```

Then, in a second terminal, pull a local model into the Ollama container
(one-time; this is the mandatory local-model path for the demo):

```bash
docker compose exec ollama ollama pull llama3.1:8b
```

- Frontend: http://localhost:5173
- Backend API + docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

No cloud API key is required to fully use the app — `LLM_PROVIDER=ollama`
by default in `.env.example`.

## Using a cloud provider instead

Edit `.env`:
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```
or
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```
Restart the backend (`docker compose restart backend`). You can also switch
providers per-request from the UI's top-bar dropdown, or per-request via the
API's `provider_override` field — no rebuild needed either way. If the
selected provider fails or is unreachable, the backend automatically falls
back to `FALLBACK_PROVIDER` (default `ollama`) and reports which provider
actually answered in both the API response and the UI message badge.

## Running manually (without Docker)

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point DATABASE_URL at your own Postgres, or use SQLite for a quick local run:
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export PYTHONPATH=.
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Set `VITE_API_BASE_URL` in `frontend/.env` (or the shell) if your backend
isn't on `http://localhost:8000`.

**Local Ollama (outside Docker):**
```bash
ollama serve
ollama pull llama3.1:8b
```
`OLLAMA_BASE_URL` defaults to `http://ollama:11434` (the Docker service
name) — set it to `http://localhost:11434` in `.env` when running manually.

## Environment variables

See `.env.example` for the full, commented list. Summary:

| Variable | Required? | Purpose |
|---|---|---|
| `DATABASE_URL` | Yes | Postgres connection string (Supabase/Railway compatible) |
| `LLM_PROVIDER` | Yes | `anthropic` \| `openai` \| `ollama` — active provider |
| `FALLBACK_PROVIDER` | Yes | Provider to fall back to on failure |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | Only if using that provider | Cloud auth |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | Yes (has defaults) | Local model config |
| `TRANSCRIPTS_DIR`, `CHUNK_SIZE_WORDS`, `CHUNK_OVERLAP_WORDS`, `TOP_K_CHUNKS` | Yes (has defaults) | RAG tuning |
| `CORS_ORIGINS` | Yes (has defaults) | Allowed frontend origins |
| `VITE_API_BASE_URL` | Yes (has defaults) | Frontend → backend URL |

**No secrets are committed.** `.env` is gitignored; only `.env.example`
(with empty key fields) is tracked.

## Refreshing the knowledge base

Drop additional Markdown files (same frontmatter format as the samples in
`backend/app/data/transcripts/`) into that directory, then either restart
the backend or call:
```bash
curl -X POST http://localhost:8000/api/kb/refresh
```
To point at a different corpus entirely, change `TRANSCRIPTS_DIR`, or
replace `app/ingestion/loader.py::load_transcripts` with a loader for your
real transcript source (a Git repo, an API, etc.) — nothing downstream
(chunking, indexing, retrieval, skills) needs to change.

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```
Covers: health/config endpoints, session lifecycle (creation, per-user
isolation, 404 handling), retrieval (indexing, relevance, chunking), and
agent routing (keyword → skill mapping, explicit-skill override). Tests run
against an in-memory SQLite DB — no live Postgres or LLM provider required.

### Manual UI test plan

1. Load the app — a session is auto-created; top bar shows KB chunk count
   and provider status.
2. Ask *"What makes a good activation metric?"* → expect a grounded answer
   citing "Finding Your Activation Metric," with a `qa` skill badge.
3. Ask *"What's the capital of France?"* → expect a polite "not covered by
   the ingested transcripts" reply, not a fabricated/off-topic answer.
4. Ask *"Write a ship 30 for 30 essay about pricing and packaging"* →
   expect the essay to open automatically in the Artifact Viewer with a
   hook, headers, bullets, and a `## Takeaway` section.
5. Ask *"Generate an html artifact summarizing product-led growth"* →
   expect it to render inside the sandboxed iframe on the right; open
   browser devtools and confirm no `<script>` executes even if you inspect
   the iframe's `srcdoc`.
6. Switch the provider dropdown to `anthropic` without a configured API key
   → send a message → expect a clear 503-based error bubble, not a hang or
   crash, and confirm the backend log shows the fallback attempt.
7. Create a second session via "New chat" → confirm its message history is
   empty and independent from the first session's.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Frontend shows "Can't reach the backend API" | Backend not running / wrong `VITE_API_BASE_URL` | Confirm `curl http://localhost:8000/api/health` returns 200; check CORS_ORIGINS includes your frontend origin |
| `/api/health` shows `"database": false` | Postgres not reachable | Check `DATABASE_URL`; if using Docker Compose, confirm the `db` service is healthy (`docker compose ps`) |
| Chat returns 503 | Neither the selected provider nor the fallback is reachable | For `ollama`, confirm the model is pulled (`docker compose exec ollama ollama list`); for cloud providers, check the API key in `.env` |
| `knowledge_base_chunks: 0` in `/api/health` | `TRANSCRIPTS_DIR` empty or misconfigured | Confirm sample `.md` files exist under `backend/app/data/transcripts/`, or POST `/api/kb/refresh` after adding files |
| HTML artifact renders blank | Expected for some sanitized-away content, or the artifact hasn't loaded yet | Check `GET /api/artifacts/{id}` directly to see the stored `content` and `sanitized` flag |
| `ModuleNotFoundError: No module named 'app'` running backend manually | `PYTHONPATH` not set | `export PYTHONPATH=.` from inside `backend/` before running uvicorn/pytest |

## Project structure

```
lenny-growth-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py, config.py, database.py, models.py, schemas.py
│   │   ├── routers/        # sessions, chat, artifacts, system
│   │   ├── agent/          # rag.py, llm_client.py, agent.py, skills/
│   │   ├── ingestion/      # transcript loader + chunker
│   │   └── data/transcripts/  # sample knowledge base
│   ├── tests/
│   ├── requirements.txt, Dockerfile, pytest.ini
├── frontend/
│   ├── src/
│   │   ├── App.tsx, api.ts, index.css
│   │   └── components/     # Sidebar, TopBar, MessageList, Composer, ArtifactViewer
│   ├── package.json, vite.config.ts, tsconfig.json, Dockerfile
├── agent-transcripts/       # coding-agent session logs (see its README)
├── docker-compose.yml
├── .env.example
├── PRD.md · design.md · architecture.md · README.md (this file)
```

## Known limitations (see PRD "Scope choices" for the full rationale)

- Single demo user, no authentication
- TF-IDF retrieval, not dense embeddings (swappable — see architecture.md)
- No scheduled transcript refresh (manual `/api/kb/refresh` only)
- No response streaming
