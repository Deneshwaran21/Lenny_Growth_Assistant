# Architecture — The Lenny Growth Assistant

## System overview

```
┌─────────────┐      HTTP/JSON      ┌──────────────────┐
│  React SPA   │ ───────────────────▶│   FastAPI backend │
│ (chat + Artifact Viewer)           │  app/main.py       │
└─────────────┘                      └─────────┬─────────┘
                                                 │
                        ┌────────────────────────┼─────────────────────┐
                        │                        │                     │
                ┌───────▼───────┐      ┌─────────▼────────┐   ┌────────▼────────┐
                │  Postgres      │      │  Agent router     │   │  Knowledge base  │
                │  (sessions,    │      │  app/agent/agent.py│   │  TF-IDF index    │
                │  messages,     │      │  → skills: qa,     │   │  over transcript │
                │  artifacts)    │      │    ship30, artifact│   │  chunks          │
                └────────────────┘      └─────────┬──────────┘   └──────────────────┘
                                                    │
                                     ┌──────────────▼───────────────┐
                                     │  LLM client (provider toggle) │
                                     │  app/agent/llm_client.py      │
                                     └───────┬─────────────┬─────────┘
                                             │             │
                                   ┌─────────▼───┐  ┌──────▼───────┐
                                   │ Anthropic /  │  │   Ollama      │
                                   │ OpenAI (cloud)│  │  (local, mandatory│
                                   └──────────────┘  │  for the demo)│
                                                      └───────────────┘
```

## Database schema (Postgres, SQLAlchemy async ORM — `app/models.py`)

**chat_sessions**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| user_id | string | indexed; demo uses a single fixed user_id |
| title | string | first 80 chars of first message, or "New chat" |
| provider | string | provider selected at session creation |
| created_at / updated_at | datetime | |
| meta | json | free-form extension point |

**chat_messages**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| session_id | FK → chat_sessions.id | indexed |
| role | string | "user" \| "assistant" \| "system" |
| content | text | |
| provider_used | string, nullable | which provider actually answered |
| sources | json | list of `SourceCitation` for grounded answers |
| skill_used | string, nullable | "qa" \| "ship30" \| "artifact" |
| created_at | datetime | |

**artifacts**
| column | type | notes |
|---|---|---|
| id | string (uuid) | PK |
| session_id | FK → chat_sessions.id | |
| message_id | string, nullable | which turn produced it |
| kind | string | "markdown" \| "html" |
| title | string | |
| content | text | sanitized before storage if kind="html" |
| sanitized | bool | true once passed through bleach |
| created_at | datetime | |

Tables are created via `Base.metadata.create_all` at startup for this
take-home; a production deployment should switch to Alembic migrations
(noted in `database.py`).

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | DB connectivity, KB chunk count, active provider |
| GET | `/api/config` | Per-provider configured/reachable status, active + fallback provider |
| POST | `/api/kb/refresh` | Re-index transcripts from `TRANSCRIPTS_DIR` without a restart |
| POST | `/api/sessions` | Create a session |
| GET | `/api/sessions?user_id=` | List a user's sessions |
| GET | `/api/sessions/{id}` | Fetch one session |
| GET | `/api/sessions/{id}/messages` | Fetch a session's message history |
| DELETE | `/api/sessions/{id}` | Delete a session (cascades to messages) |
| POST | `/api/chat` | Main conversational turn — see contract below |
| GET | `/api/artifacts/{id}` | Fetch a generated artifact |

### `POST /api/chat` contract
Request:
```json
{
  "session_id": "uuid",
  "message": "What makes a good activation metric?",
  "provider_override": "anthropic | openai | ollama | null",
  "skill": "auto | qa | ship30 | artifact"
}
```
Response:
```json
{
  "session_id": "uuid",
  "message_id": "uuid",
  "reply": "...",
  "provider_used": "ollama",
  "skill_used": "qa",
  "sources": [{"transcript_id": "...", "episode_title": "...", "chunk_id": "...", "excerpt": "..."}],
  "artifact_id": "uuid | null",
  "grounded": true
}
```
Validation: `message` is length-bounded (1–8000 chars) via Pydantic;
`session_id` must reference an existing session (404 otherwise);
`provider_override`/`skill` are constrained to enum values, so malformed
input is rejected at the schema layer before it reaches the agent.
Failures return typed JSON errors (404 for missing session, 503 for "no LLM
provider reachable") rather than raw tracebacks; a global exception handler
in `main.py` converts any unhandled exception to a generic 500 with server-
side logging, never leaking internals to the client.

## Ingestion / retrieval flow

1. **Load** — `app/ingestion/loader.py::load_transcripts` reads every `.md`
   file under `TRANSCRIPTS_DIR`, parses YAML frontmatter
   (`episode_title`, `episode_id`, `source_url`) and body text.
2. **Chunk** — a sliding-window word chunker (`CHUNK_SIZE_WORDS`,
   `CHUNK_OVERLAP_WORDS`, defaults 220/40) splits each transcript into
   overlapping chunks, each retaining a `chunk_id` of the form
   `{episode_id}::chunk-{n}` for traceability back to source.
3. **Index** — `app/agent/rag.py::KnowledgeBase` fits a TF-IDF vectorizer
   over all chunks at startup (and on-demand via `/api/kb/refresh`).
4. **Retrieve** — cosine similarity between the query vector and all chunk
   vectors; top-K above a relevance floor (`MIN_RELEVANCE = 0.05`) are
   returned with their source metadata.
5. **Trace back to source** — every citation returned to the client includes
   `episode_title`, `transcript_id`, `chunk_id`, and a short excerpt, so an
   evaluator can verify grounding against the source file directly.
6. **Refresh** — `POST /api/kb/refresh` rebuilds the index from disk without
   a process restart, simulating periodic transcript updates.

**Swapping to a real corpus:** point `TRANSCRIPTS_DIR` at a directory of
similarly-formatted Markdown files (or replace `load_transcripts` with a
loader for your actual repo/API) — nothing downstream changes.

**Swapping to dense embeddings:** `KnowledgeBase` is the single integration
point; setting `EMBEDDING_BACKEND=sentence-transformers` is designed to swap
the vectorizer without touching routers, skills, or the agent.

## Agent routing

`app/agent/agent.py::detect_intent` is a deliberately simple, transparent,
zero-latency keyword router (see PRD "Scope choices" for why a second LLM
call wasn't used for routing in this build):
- Explicit `skill` field in the request always wins.
- Otherwise, keyword match against `ARTIFACT_KEYWORDS` / `SHIP30_KEYWORDS`;
  default falls through to grounded QA.

Each skill (`qa.py`, `ship30.py`, `artifact.py`) is an independent module
with its own system prompt and grounding rules — skill boundaries are file
boundaries, so extending or auditing one skill never risks the others.

## Model toggle & fallback (`app/agent/llm_client.py`)

- `LLM_PROVIDER` (env or per-request `provider_override`) selects
  `anthropic`, `openai`, or `ollama`.
- Each provider has an isolated async function (`_call_anthropic`,
  `_call_openai`, `_call_ollama`) behind a common `LLMResult` interface.
- `generate()` tries the selected provider; on any exception (missing key,
  timeout, non-2xx, connection refused) it logs a structured warning and
  falls back once to `FALLBACK_PROVIDER` (default `ollama`, since it has no
  external dependency). If the fallback also fails, `LLMUnavailableError` is
  raised and the chat router returns **503**, not a 500 or a silent hang.
- `GET /api/config` exposes per-provider `configured`/`reachable` status so
  the evaluator can see toggle state without reading logs.

## Artifact security

Two independent layers, so a failure in one doesn't grant script execution:

1. **Server-side sanitization** (`app/agent/skills/artifact.py`) — HTML
   artifacts are passed through `bleach.clean()` with an explicit tag/
   attribute allowlist before being stored. `<script>` tags, event-handler
   attributes (`onclick`, etc.), and non-`http(s)/mailto` URI schemes
   (including `javascript:`) are stripped. The `style` attribute is
   deliberately **not** allowlisted (bleach can't safely sanitize arbitrary
   CSS without an extra CSS sanitizer dependency, so it's simpler and safer
   to disallow it entirely); a single top-level `<style>` block is allowed
   for the HTML-artifact skill's own scoped CSS.
2. **Client-side sandboxing** (`frontend/src/components/ArtifactViewer.tsx`)
   — HTML artifacts are rendered via `<iframe sandbox="" srcDoc={...}>`. The
   empty `sandbox` attribute applies the strictest default: no script
   execution, no form submission, no top-level navigation, no popups, no
   same-origin access to the parent page. Markdown artifacts are rendered
   with `react-markdown` **without** the `rehype-raw` plugin, so raw HTML
   embedded inside Markdown is never executed either.

What the viewer explicitly **permits**: styled static markup, images from
http(s) sources, tables, lists — anything a document/snippet legitimately
needs. What it **blocks**: all script execution, all navigation out of the
frame, all access to cookies/localStorage/parent DOM, regardless of what
survives sanitization.

## Deployment topology

`docker-compose.yml` runs four services: `db` (Postgres 16), `ollama`
(local model runtime, model pulled once via
`docker compose exec ollama ollama pull llama3.1:8b`), `backend` (FastAPI,
depends on `db` healthcheck), `frontend` (static Vite build served via
`serve`). All configuration flows through `.env` (see `.env.example`); no
secrets are committed. For a hosted Postgres, replace `DATABASE_URL` with a
Supabase/Railway connection string — no other change is required.

## Observability & resilience

- Structured logging (`logging.basicConfig` with timestamps + named loggers
  per module: `lenny.agent`, `lenny.rag`, `lenny.llm`, `lenny.chat`,
  `lenny.system`) makes it possible to trace a single request from routing
  decision → retrieval hit count → provider used → fallback (if any).
- `/api/health` distinguishes `ok` / `degraded` / `down` based on DB
  connectivity and whether the knowledge base has any indexed chunks —
  useful for both manual debugging and container orchestration healthchecks.
- Failure modes explicitly handled without crashing the request: missing
  API keys, unreachable Ollama, LLM timeouts (`LLM_TIMEOUT_SECONDS`), empty
  retrieval results (explicit "not covered" reply), and DB connection
  failures (surfaced via `/api/health`, not a hung request).
