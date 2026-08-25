# AMPM Service POS Troubleshooting Assistant — Phase 1 (PoC)

A cloud-ready, local RAG (Retrieval-Augmented Generation) troubleshooting assistant for AMPM Service field support technicians working on retail POS registers, PIN pads, and store servers.

Ingests technical manuals (LOC Software's SMS POS, Verifone M400, Buypass/Fiserv payment processing), stores page-aware vector chunks in a local persistent ChromaDB store, and delivers fast, page-cited troubleshooting answers.

---

## Technical Features

- **PDF Ingestion & Auto-Categorization**: Page-by-page text extraction with PyMuPDF/pypdf, ~500-token overlapping chunks, and automatic categorization (*Verifone Hardware, Buypass Config, SMS Software, Server Config, Network / Connectivity*).
- **Persistent Vector Store**: `ChromaDB` local persistent vector database.
- **Embeddings**: Google Gemini `text-embedding-004`.
- **Pluggable Multi-Provider LLM Layer**: Single unified `generate_answer(context, question)` interface supporting:
  1. **Google Gemini API** (`gemini-2.5-flash` / `gemini-1.5-flash` - default)
  2. **Groq API** (`llama-3.3-70b-versatile`)
  3. **Ollama Local Server** (`llama3` / `mistral`)
- **CLI Terminal Interface**: Full-featured CLI (`cli.py`) supporting document ingestion, queries, provider selection, category filtering, and interactive chat mode with `rich` UI formatting.

---

## Quickstart Guide

### 1. Environment Setup

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_google_gemini_api_key
GROQ_API_KEY=your_groq_api_key_optional
DEFAULT_LLM_PROVIDER=gemini
```

### 2. Ingest Sample Documentation

Place PDF files into `./sample_docs/` (or run `python create_sample_docs.py` to generate test manuals):

```bash
.\.venv\Scripts\python.exe cli.py ingest --dir ./sample_docs
```

### 3. Ask Troubleshooting Questions

Ask a symptom question via the CLI:

```bash
# Query using default provider (Gemini)
.\.venv\Scripts\python.exe cli.py query "How do I fix the M400 cash-back 10x amount error?"

# Filter query by document category
.\.venv\Scripts\python.exe cli.py query "M400 power reset" --category "Verifone Hardware"

# Switch LLM Provider on the fly
.\.venv\Scripts\python.exe cli.py query "Buypass host timeout error" --provider groq

# Start interactive chat session
.\.venv\Scripts\python.exe cli.py interactive
```

---

## Project Structure

```
SMS_Project/
├── config.py                 # Environment & model configuration
├── cli.py                    # Command-Line Application (Ingest / Query / Interactive)
├── create_sample_docs.py     # Script generating sample POS manuals for PoC testing
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── ingestion/
│   ├── pdf_parser.py         # PDF text & metadata extraction
│   └── chunker.py            # Text chunking (~500 tokens) & auto-categorization
├── vectorstore/
│   ├── embeddings.py         # Gemini text-embedding-004 adapter for ChromaDB
│   └── chroma_store.py       # Persistent ChromaDB vector DB manager
├── llm/
│   ├── base.py               # Abstract LLM provider interface
│   ├── gemini_provider.py    # Google Gemini API adapter
│   ├── groq_provider.py      # Groq API adapter
│   ├── ollama_provider.py    # Ollama local endpoint adapter
│   └── factory.py            # Provider selector factory
└── rag/
    └── engine.py             # RAG retrieval & prompt grounding pipeline
```

---

## Roadmap

- **Phase 1 (Complete)**: Local Python RAG ingestion, ChromaDB vector store, pluggable multi-provider LLM layer, CLI.
- **Phase 2**: Migrate ChromaDB vector store to Supabase (`pgvector`), stand up Node.js/FastAPI backend, and deploy static HTML/JS web chat UI on Vercel/Netlify.
- **Phase 3**: Auth allowlist for AMPM staff, admin PDF upload dashboard, and ticket feedback loop.
