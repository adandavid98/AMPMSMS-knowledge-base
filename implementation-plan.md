# AMPM Service POS Troubleshooting Assistant — Implementation Plan

## 1. Project Summary

A cloud-hosted, chatbot-style tool that ingests AMPM Service's SMS POS (LOC Software) documentation — Verifone M400, Buypass/Fiserv, register and server manuals, ini config references, known-issue writeups — and lets techs describe a symptom on a register or server and get fast, cited troubleshooting steps instead of manually searching PDFs.

**Constraints from scoping:**
- Cloud-hosted, accessible to coworkers (multi-user)
- Custom build (not an off-the-shelf tool), but keep to free/low-cost tiers
- 20–100 source PDFs to start, expected to grow
- Requires approval before deployment — plan should be presentable to a decision-maker

## 2. Architecture Overview

```
[Admin: PDF upload] → [Ingestion pipeline] → [Vector DB]
                                                   ↑
[Tech: chat UI] → [Backend API] → [Retrieval] → [Claude API] → [Answer + source citations]
```

**Components:**

| Layer | Choice | Why |
|---|---|---|
| Frontend | Static HTML/JS chat UI (or lightweight React) | Matches your existing HTML-first instincts, cheap to host, easy to brand for AMPM |
| Backend API | Node.js (Express) or Python (FastAPI) | Thin layer: handles retrieval + calls Claude API |
| Vector store | Supabase (Postgres + pgvector) free tier, or Chroma Cloud free tier | Free tier covers 20–100 docs easily; Supabase also gives you auth + a Postgres DB for logging in one place |
| Embeddings | Voyage AI (Anthropic's recommended embeddings partner) or open-source model via API | Needed to turn PDF chunks into searchable vectors |
| LLM | Pluggable: Google Gemini API, Groq API, or self-hosted Ollama | See §2.1 below — build to swap between all three |
| Hosting (frontend) | Vercel or Netlify free tier | Zero-cost static hosting with HTTPS |
| Hosting (backend) | Render or Fly.io free/hobby tier (Ollama needs its own host — see §2.1) | Free tier sufficient at this scale |
| Auth | Simple shared login or Supabase Auth (email allowlist for AMPM staff) | Keeps it internal without building auth from scratch |
| PDF storage | Supabase Storage or S3 free tier | Keep original PDFs alongside their vector chunks, so answers can link back to "see page X of doc Y" |

**Estimated ongoing cost at this scale:** $0/month if running fully on Gemini/Groq free tiers and free hosting; small hosting cost (~$5-10/mo) only if self-hosting Ollama on a dedicated small VM.

### 2.1 Multi-provider LLM layer

Rather than picking one LLM up front, the backend will have a single "answer generation" function with an interchangeable provider, so all three can be wired in and swapped (or compared) without touching the rest of the app:

| Provider | Role in this project | Notes |
|---|---|---|
| **Google Gemini API** (Gemini 2.5 Flash) | Primary default | Generous free tier, good quality, simplest to get running first |
| **Groq API** (Llama/Mixtral) | Fast alternate / fallback | Free tier, very low latency — good for quick lookups during live troubleshooting |
| **Ollama self-hosted** (e.g. Llama 3.1 8B or Mistral 7B) | Fully offline/free option | No per-query cost or external dependency at all, but needs its own always-on host (a small VM with enough RAM — 8B models want ~8GB+) since Render/Vercel free tiers can't run it directly |

**Implementation approach:**
- Backend exposes one internal interface, e.g. `generateAnswer(context, question, provider)`, with a thin adapter per provider (each just wraps that provider's chat completion call).
- A config value (or even a dropdown in the admin/chat UI) selects which provider handles a given request — lets you A/B quality and latency across all three with the same retrieved context.
- Ollama requires a persistent host (a small always-on VM — e.g. a free-tier Oracle Cloud instance or a cheap DigitalOcean droplet) since it's not a hosted API; Gemini and Groq are just API keys with no infra to manage.
- Recommended default order to bring online: **Gemini first** (fastest to a working demo) → **Groq** (compare speed/quality) → **Ollama** (once you're ready to stand up a dedicated host, for a zero-external-dependency option).

## 3. Core Workflow

### 3.1 Ingestion (admin-side, run when new docs arrive)
1. Upload PDF via a simple admin page or a local script.
2. Extract text per page (and OCR any scanned pages — some LOC/Verifone docs may be scans).
3. Chunk text into overlapping sections (e.g. ~500 tokens, 50-token overlap), tagging each chunk with: source filename, page number, and a rough category (Verifone hardware / Buypass config / SMS software / server / network).
4. Generate embeddings for each chunk, store in the vector DB alongside metadata.

### 3.2 Query (tech-side, at point of use)
1. Tech types the symptom, e.g. "M400 cash-back other amount showing 10x."
2. Backend embeds the query, retrieves top-N matching chunks from the vector DB.
3. Chunks + query are sent to the active LLM provider (Gemini, Groq, or Ollama — see §2.1) with a system prompt instructing it to answer only from the provided context, cite the source doc/page, and flag when the docs don't cover the issue (rather than guessing).
4. Answer is returned with expandable "source" links back to the original PDF page.

### 3.3 Feedback loop (important for a troubleshooting tool)
- Thumbs up/down on each answer, optionally "this fixed it" tagging.
- Logged answers become a growing internal knowledge base of resolved issues even beyond the source PDFs — this is where the real long-term value builds.

## 4. Suggested Build Phases

**Phase 1 — Proof of concept (no cloud hosting yet)**
- Load 5–10 representative PDFs into a local tool like AnythingLLM or Open WebUI + Ollama.
- Test retrieval quality against real past tickets (e.g. the M400 cash-back 10x issue, the Zebra ZQ620 WiFi drop).
- Goal: confirm the documents actually answer the kinds of questions techs ask, before investing in a custom build.

**Phase 2 — Minimal cloud build**
- Stand up vector DB (Supabase) + backend API + Claude API integration.
- Basic HTML chat frontend, single shared login.
- Ingest the full 20–100 doc set.
- Internal test with a handful of real store issues.

**Phase 3 — Hardening for coworker rollout**
- Per-user login (or at least per-store), usage logging, feedback capture.
- Category filters (e.g. "Verifone only") for faster narrowing.
- Admin upload page so new PDFs don't require a script/dev.

**Phase 4 — Knowledge base growth**
- Feed resolved/logged tickets back into the corpus.
- Optional: structured symptom → fix index alongside the chat, for the most common recurring issues (fast lookup without waiting on LLM generation).

## 5. Scaling Beyond the Initial Doc Set

The architecture has no hard document ceiling — adding a PDF is just adding rows to the vector store, not retraining anything.

- **Progressive upload is native to this design.** New PDFs can be added anytime via the admin upload flow (§3.1) with no downtime or rebuild; they're searchable within seconds of ingestion.
- **Free-tier limits to watch:** Supabase's free tier (500MB DB + 1GB file storage) comfortably covers roughly 300-1000 PDFs at typical size — well past the initial 20-100. Worth revisiting hosting tier once you approach that range.

## 6. Approval Package — What to Prepare

Since this needs sign-off, worth preparing:
- 1-page summary of the problem (time lost searching PDFs during live register/server issues) and the proposed fix.
- Cost estimate (near-zero at this scale, itemized by service).
- Data handling note: where the PDFs and any store-specific data live, who can access them, that it's internal-only.
- Phase 1 proof-of-concept results (if run before requesting approval, this makes the ask much easier — "here's it already answering real questions" beats a hypothetical).

## 8. Kickoff Prompt

Use this prompt (e.g. with Claude Code, or a fresh chat) to start Phase 1 development:

```
I'm building a cloud-hosted RAG (retrieval-augmented generation) chatbot for
internal troubleshooting support at AMPM Service, a retail POS company. 
Techs need to describe symptoms on registers/servers (LOC Software's SMS POS,
Verifone M400 PIN pads, Buypass/Fiserv payment processing) and get fast,
cited answers pulled from our internal PDF documentation (20-100 PDFs to
start, growing over time via progressive upload).

ARCHITECTURE (already scoped, please follow this):
- Frontend: static HTML/JS chat interface
- Backend: Node.js (Express) or Python (FastAPI) — thin API layer
- Vector store: Supabase (Postgres + pgvector), free tier
- Embeddings: Voyage AI or an open-source embedding model via API
- LLM layer: pluggable across three providers — Google Gemini API (default),
  Groq API (fast alternate), and self-hosted Ollama (zero-dependency
  option) — via one shared generateAnswer(context, question, provider)
  interface with a thin adapter per provider
- PDF storage: Supabase Storage
- Hosting: Vercel/Netlify (frontend), Render/Fly.io (backend)
- Auth: simple shared login or Supabase Auth with an email allowlist

START WITH PHASE 1 (proof of concept, no cloud hosting yet):
1. Set up a local project structure for ingestion + retrieval only
   (no frontend, no deployment yet).
2. Build a PDF ingestion script: extract text per page (OCR fallback for
   scanned pages), chunk into ~500-token overlapping sections, tag each
   chunk with source filename, page number, and category
   (Verifone hardware / Buypass config / SMS software / server / network).
3. Store chunks + embeddings in a local vector store (can be local Chroma
   for this phase, migrate to Supabase pgvector in Phase 2).
4. Build a simple query function: embed the question, retrieve top-N
   chunks, send to Gemini API with a system prompt that answers ONLY from
   the provided context, cites source doc + page, and explicitly says
   when the docs don't cover something rather than guessing.
5. Give me a basic CLI or minimal script I can run locally to test
   retrieval quality against a handful of real past issues before we
   build anything further.

Ask me for my Gemini API key setup and a sample folder of PDFs before
writing the ingestion script. Keep everything in Phase 1 local and
free — no cloud deployment until this is validated.
```

## 9. Open Questions to Resolve Before Building
- ~~Do any PDFs contain sensitive info (merchant IDs, credentials, store-specific configs) that should be redacted or access-restricted?~~ **Resolved: No** — PDFs don't contain sensitive info requiring redaction or restriction.
- ~~Should access be all AMPM techs, or scoped by role/store?~~ **Resolved: Open to all AMPM techs** — auth can use a single shared allowlist rather than role/store-based permissions, simplifying the auth layer in §2.
- Is there an existing ticketing system (for Phase 4 feedback-loop integration) worth connecting to later?
