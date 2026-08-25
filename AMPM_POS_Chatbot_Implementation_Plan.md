# AMPM Service — SMS POS (LOC) Troubleshooting Chatbot
## Implementation Plan

---

## 1. Goal

Build a cloud-hosted chatbot that lets AMPM Service technicians ask natural-language troubleshooting questions about the SMS POS (LOC) system — including Verifone M400 and Buypass (Fiserv) payment processing — and get accurate, cited answers pulled from internal documentation. If the internal knowledge base doesn't have the answer, the bot falls back to a web search instead of guessing or refusing.

---

## 2. Architecture Overview

```
User query
   │
   ▼
[1. Query understanding]  — Groq (fast/cheap)
   │
   ▼
[2. Semantic + keyword retrieval]  — vector DB (pgvector/Qdrant)
   │
   ▼
[3. Relevance check]
   │
   ├── Found in KB ──► [4a. Answer generation w/ citations] — Gemini
   │
   └── Not found ────► [4b. Tavily web search] ──► [4c. Answer generation, flagged as external] — Gemini
   │
   ▼
Response streamed to user (with source: "Internal Docs" or "Web")
```

---

## 3. Components & Stack

| Layer | Tool | Notes |
|---|---|---|
| Document storage | Cloud bucket (S3/GCS/Supabase Storage) | Store original PDFs |
| Chunking | Custom script (Python) | Chunk by section/procedure, not fixed char count |
| Embeddings | Gemini `text-embedding-004` | Embed both docs and queries |
| Vector DB | Supabase (pgvector) or Qdrant Cloud | Hybrid search: vector + keyword/BM25 |
| Query understanding / reranking | Groq (Llama 3.3 70B) | Fast, cheap, low latency |
| Final answer generation | Gemini | Better long-context handling |
| Web fallback search | **Tavily API (free tier)** | 1,000 free queries/month, no card required |
| Backend | Python (FastAPI) or Node (Express) | Orchestrates the pipeline |
| Frontend | Simple chat UI (Next.js/Streamlit) | Streaming responses |

---

## 4. Step-by-Step Implementation

### Phase 1 — Document Ingestion
1. Collect all SMS POS / LOC documentation PDFs (20–100 docs).
2. Extract text (preserve section headers, error codes, page numbers as metadata).
3. Chunk semantically — target one troubleshooting procedure or error-code entry per chunk. Keep chunks ~300–800 tokens.
4. Generate embeddings for each chunk via Gemini's embedding model.
5. Store chunks + embeddings + metadata (`source_file`, `section_title`, `page_number`) in the vector DB.

### Phase 2 — Retrieval Pipeline
1. On each user query, embed the query with the same embedding model.
2. Run **hybrid search**: vector similarity (top ~8) + keyword/full-text match for exact terms (error codes, model numbers like "M400", "E-102").
3. Optional: rerank the top results with a cheap Groq call — ask it to pick which snippets actually answer the question.
4. Pass the top 3–5 reranked chunks into the generation step.

### Phase 3 — Answer Generation (internal KB)
1. Send the retrieved chunks + user question to Gemini using the **Internal KB System Prompt** (Section 6 below).
2. If the model returns the sentinel `NOT_FOUND_IN_KB`, trigger Phase 4 (web fallback) instead of returning that raw output to the user.
3. Otherwise, stream the cited answer back to the user.

### Phase 4 — Web Fallback (Tavily)
1. Call the **Tavily Search API** (`https://api.tavily.com/search`) with the user's query, scoped with extra context terms like `"LOC SMS POS"`, `"Verifone M400"`, `"Buypass Fiserv"` appended to reduce noise.
2. Use Tavily's **basic** search depth (not "advanced") to keep latency low — advanced mode can take 5+ seconds.
3. Pass the returned snippets into Gemini using the **Web Fallback System Prompt** (Section 6 below).
4. Clearly label the response in the UI as **"Answer from web search — not verified company documentation."**

### Phase 5 — Conversation Memory & Streaming
1. Store the last 4–6 turns of conversation per session and include them in each new pipeline call, so follow-ups like "what about the pin pad specifically" resolve correctly.
2. Stream tokens to the frontend via SSE or websockets for a responsive feel.

### Phase 6 — Deployment
1. Backend: containerize (Docker) → deploy to Cloud Run / Render / Railway.
2. Vector DB: Supabase (managed, free tier available) or Qdrant Cloud.
3. Secrets: Gemini API key, Groq API key, Tavily API key stored in environment variables / secret manager — never hardcoded.
4. Add basic auth or SSO restriction since this is for internal coworkers only.

### Phase 7 — Evaluation & Iteration
1. Build a small test set of ~20 real troubleshooting questions with known correct answers from the docs.
2. Check: does retrieval pull the right chunks? Does the model cite correctly? Does it correctly trigger web fallback when it should?
3. Tune chunk size, top-k, and reranking based on failures.

---

## 5. Tavily Free Tier — Web Fallback Details

- **Free tier**: 1,000 API credits/month, no credit card required.
- **Why Tavily over alternatives**: purpose-built for LLM/RAG use — returns clean, pre-summarized content instead of raw HTML links, so no scraping/parsing step needed on your end.
- **Endpoint**: `POST https://api.tavily.com/search`
- **Basic request shape**:
```json
{
  "api_key": "YOUR_TAVILY_KEY",
  "query": "Verifone M400 pin pad communication error LOC SMS POS",
  "search_depth": "basic",
  "max_results": 5
}
```
- **Caution**: Brave Search API's free tier was discontinued in Feb 2026 — do not architect around it. Serper.dev is a viable cheap paid backup (2,500 one-time free queries, then ~$0.30–$1.00/1k) if Tavily's monthly quota gets tight, but it returns raw SERP data requiring your own scraping.

---

## 6. System Prompts

### 6a. Internal KB System Prompt (Gemini, Phase 3)

```
You are the AMPM Service technical support assistant for SMS by LOC point-of-sale systems.

You will be given retrieved documentation excerpts and a user's question.

Rules:
1. Answer ONLY using the provided excerpts. Do not use outside knowledge unless explicitly told the excerpts are insufficient.
2. If the excerpts fully answer the question, give clear, numbered troubleshooting steps.
3. Always cite which document/section each step comes from, e.g. "(Source: SMS_POS_Manual_Ch4.pdf, p.12)".
4. If the excerpts are partial or ambiguous, say what's missing and ask a clarifying question rather than guessing.
5. If the excerpts are irrelevant to the question, respond exactly with: NOT_FOUND_IN_KB
   (the system will then trigger a web search — do not attempt to answer from general knowledge yourself)
6. Keep the tone practical and step-by-step, like a technician talking to another technician.
```

### 6b. Web Fallback System Prompt (Gemini, Phase 4)

```
No internal documentation matched this question. You are now answering using web search results instead of company documentation.

Rules:
1. Base your answer only on the provided web search snippets.
2. Clearly state at the start of your answer that this information comes from external web sources, not verified AMPM/LOC documentation, and should be confirmed against official LOC or Verifone support channels before being applied — especially for anything involving payment processing or PCI-relevant settings.
3. If the web results appear to describe a different POS system, payment processor, or hardware model than what was asked about, say so explicitly rather than answering as if it matches.
4. Give clear, numbered steps where possible, citing which source each step comes from.
5. If the web results don't answer the question either, say so plainly and suggest contacting LOC support directly.
```

### 6c. Query Understanding / Rewrite Prompt (Groq, Phase 2 — optional but recommended)

```
You rewrite technician support questions into a clean search query for a documentation retrieval system.

- Preserve exact error codes, model numbers, and product names exactly as written (e.g. "M400", "E-102", "Buypass").
- Expand vague phrasing into likely technical terms if context makes it obvious.
- Output ONLY the rewritten query, nothing else.
```

---

## 7. Open Decisions to Confirm Before Building

- Vector DB choice: Supabase pgvector vs Qdrant Cloud
- Backend framework: FastAPI vs Express
- Where credentials/API keys will be stored for the team
- Internal auth method for coworker access
