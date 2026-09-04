# PRD — The Lenny Growth Assistant

## 1. Forward Deployment Brief

### User and problem
**Primary user:** a product manager or growth lead at a company evaluating this
internal tool — someone who reads (or wishes they had time to read) Lenny's
Podcast/Newsletter, and wants fast, trustworthy answers to "what does the best
current thinking say about X" without re-listening to hours of episodes or
trusting their memory of a transcript they skimmed six months ago.

**Job to be done:** "When I'm making a product/growth decision (pricing tier,
activation metric, PLG motion), help me quickly recall and apply the relevant,
sourced advice from Lenny's guests — and let me turn that into something I can
ship (a written brief, an essay, a shareable doc) without copy-pasting quotes
by hand."

**Pain removed:** the assistant removes (a) the time cost of searching across
dozens of long transcripts, (b) the risk of misremembering or misattributing
advice, and (c) the extra step of manually reformatting a good answer into a
polished, shareable artifact.

### Success metric
Primary (product): **% of chat turns that return a grounded answer** (i.e.
`grounded: true` in the API response) rather than an "I don't have material on
that" fallback, tracked per session. Target for the demo corpus: **≥ 80%** for
on-topic questions (PLG, activation, pricing/packaging — the three ingested
episodes).

Secondary (operational): **p95 end-to-end response latency** for a grounded
chat turn, measured separately for the cloud provider and the local Ollama
path, so an operator can see the real cost of "local-first."

### Assumptions
Because the brief describes "Lenny's Podcast transcripts" without providing an
actual dataset or repo link, this build makes the following explicit
assumptions:
- The evaluator does not require a live scrape of a specific transcript
  archive. The ingestion pipeline is built against a small, realistic set of
  representative sample transcripts (3 episodes, Markdown + YAML frontmatter)
  stored in `backend/app/data/transcripts/`, and is architected so pointing
  `TRANSCRIPTS_DIR` at a real corpus (or swapping the loader for one that
  pulls from a Git repo/API) requires no other code changes.
- A single demo user/tenant is sufficient — no auth/multi-tenant model is
  required for this assessment (see Scope choices).
- "Anthropic Claude Agent SDK or Pi Coding Agent" is interpreted as "the agent
  layer should call an Anthropic-compatible messages API and support
  tool/skill routing," implemented directly against the Claude Messages API
  rather than a specific SDK version, since SDK availability/version wasn't
  specified. Swapping in the official Agent SDK is a contained change inside
  `app/agent/llm_client.py`.
- "PostgreSQL... You may use Supabase or Railway" is interpreted as: ship
  against standard Postgres via `DATABASE_URL`, run via docker-compose locally
  for the graded demo, and document (not necessarily provision) how to point
  it at Supabase/Railway.
- Local model quality/latency on a modest laptop is acceptable to be lower
  than the cloud model — the toggle exists precisely so the evaluator can
  compare both, not because local is expected to win on quality.

### Scope choices
**Included:**
- Grounded RAG Q&A with source citations and explicit "not covered" fallback
- Ship 30 for 30 essay generation as a distinct, rule-encoded skill
- Markdown + HTML artifact generation with a sanitized, sandboxed viewer
- Session persistence (Postgres), independent per-session context
- Cloud (Anthropic/OpenAI) + local (Ollama) provider toggle with fallback
- Structured logging, health/config endpoints, graceful degradation
- Docker Compose one-command startup, automated tests, this documentation set

**Explicitly excluded (and why):**
- **Authentication/multi-user accounts** — out of scope for a take-home; a
  single demo `user_id` is used. Adding real auth is a bounded follow-up
  (see architecture.md).
- **Automatic/scheduled transcript refresh from a live source** — the
  ingestion pipeline supports manual refresh (`POST /api/kb/refresh`) and a
  swappable loader, but there's no scheduler/webhook in this build; polling a
  real transcript source wasn't specified precisely enough to build against.
- **Streaming token-by-token responses** — the UI shows a single "Thinking…"
  state rather than a streaming typewriter effect, to keep the agent/router
  boundary simple for this assessment; the backend architecture doesn't block
  adding SSE/websockets later.
- **Fine-grained RBAC on artifacts** (who can view/edit which artifact) —
  every artifact is scoped to its session only.
- **A vector database (pgvector/Pinecone/etc.)** — TF-IDF cosine similarity
  over transcript chunks was chosen for a corpus this size (see Risks below);
  the retrieval interface is the single swap point for real embeddings.

### Risks and trade-offs
| Risk | Mitigation in this build |
|---|---|
| **Hallucination** | QA and Ship30 skills only answer from retrieved chunks; below a relevance floor, the assistant explicitly declines rather than guessing. System prompts forbid outside knowledge. |
| **Retrieval quality at scale** | TF-IDF is fast and dependency-light but weaker than dense embeddings on paraphrased queries. `EMBEDDING_BACKEND` is a config toggle so swapping to sentence-transformers is a contained change, not a rewrite — worth doing before ingesting the full transcript corpus. |
| **Latency (cloud vs. local)** | Local Ollama on a laptop is meaningfully slower/lower-quality than a hosted model; the UI surfaces which provider actually answered so this trade-off is visible, not hidden. |
| **Cost** | Cloud calls are opt-in via API key; with no key configured the system runs entirely on local Ollama at zero marginal cost. |
| **Unsafe artifact rendering** | HTML artifacts are sanitized server-side (bleach allowlist) *and* rendered client-side inside a `sandbox=""` iframe with no `allow-scripts` — a belt-and-suspenders approach so a bypass of one layer doesn't grant script execution. See architecture.md#artifact-security. |
| **Data leakage across sessions** | Each chat session is a separate DB row with its own message history; the agent only ever receives history scoped to the current `session_id`. |
| **Provider/dependency failure** | Missing API keys, an unreachable Ollama, DB connection failures, and empty retrieval results all degrade gracefully (typed errors, `/api/health`, no silent 500s) rather than crashing the request. |

## 2. Users and flows
1. **Start a session** → sidebar "New chat" → backend creates a `ChatSession` row.
2. **Ask a grounded question** → router detects `qa` intent → retrieval →
   LLM call scoped to retrieved chunks → answer + citations rendered inline.
3. **Ask for a Ship 30/30 essay** → router detects `ship30` intent (or user
   explicitly selects the skill chip) → essay generated as a Markdown
   artifact → opens automatically in the Artifact Viewer.
4. **Ask for an artifact** ("generate an HTML snippet of this") → router
   detects `artifact` intent → HTML/Markdown generated, sanitized if HTML,
   stored, and opened in the viewer beside the chat.
5. **Switch model provider** mid-session via the top-bar dropdown → next
   message uses the new provider; UI shows which provider actually answered.
6. **Evaluator checks health** → `GET /api/health` reports DB connectivity,
   knowledge-base chunk count, and active provider for quick diagnosis.

## 3. Acceptance criteria
- [ ] A new session can be created and independently maintains its own
      message history across multiple turns.
- [ ] A grounded question about PLG/activation/pricing returns an answer that
      cites at least one transcript episode by title.
- [ ] A question clearly outside the ingested corpus returns
      `grounded: false` and an explicit "not covered" message — never a
      fabricated answer.
- [ ] A Ship 30/30 request produces a Markdown artifact with a hook, headers,
      bullets, and a `## Takeaway` section, viewable in the Artifact Viewer.
- [ ] An HTML artifact request with an injected `<script>` payload in the
      model output is stripped before storage and before render — verified
      by an automated test.
- [ ] Switching `LLM_PROVIDER` (or the UI dropdown) between `anthropic`,
      `openai`, and `ollama` changes which provider answers, without code
      changes.
- [ ] Stopping Ollama (or omitting a cloud API key) results in a clear,
      typed error surfaced to the UI — not a stack trace or silent hang.
- [ ] `docker compose up` brings up db + ollama + backend + frontend with a
      documented one-time model pull step.

## 4. Implementation plan (as executed)
1. Backend skeleton: config, DB models, schemas, health endpoints.
2. Ingestion + retrieval (TF-IDF) over sample transcripts.
3. LLM client abstraction with provider fallback.
4. Three skills (QA, Ship30, Artifact) + keyword-based router.
5. Chat/session/artifact routers wired to skills; automated tests for each
   layer, run and passing before moving on.
6. Frontend: session sidebar, chat pane, sandboxed Artifact Viewer, provider
   toggle — typechecked and production-built to confirm it compiles clean.
7. Docker Compose, `.env.example`, documentation set (this PRD +
   architecture.md + design.md + README.md).
