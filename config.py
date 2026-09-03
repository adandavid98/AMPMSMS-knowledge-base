import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).parent.resolve()

# API Keys & Endpoints
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY") or os.getenv("CohereAMPM_API_KEY") or os.getenv("COHEREAMPM_API_KEY") or ""
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
TAVILY_SEARCH_URL = "https://api.tavily.com/search"

# Langfuse Observability
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Pipeline Enhancements
USE_DOCLING_PARSER = os.getenv("USE_DOCLING_PARSER", "true").lower() in ("true", "1", "yes")
USE_HYBRID_SEARCH = os.getenv("USE_HYBRID_SEARCH", "true").lower() in ("true", "1", "yes")

# Supabase Cloud Vector DB
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Authentication & Access Control
REQUIRE_AUTH = os.getenv("REQUIRE_AUTH", "true").lower() in ("true", "1", "yes")
ALLOWED_EMAIL_DOMAIN = os.getenv("ALLOWED_EMAIL_DOMAIN", "@ampmservice.com").lower()
APP_PASSPHRASE = os.getenv("APP_PASSPHRASE", "AMPM$$16520")

# Defaults
DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "gemini").lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")  # Primary active Flash model
GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"

COHERE_MODEL = "command-r-08-2024"
GROQ_MODEL = "llama-3.3-70b-versatile"
OPENROUTER_MODEL = "dots-studio/dots-3-note-preview:free"
OLLAMA_MODEL = "llama3"

# Chunking & Storage
CHROMA_PERSIST_DIR = str(BASE_DIR / os.getenv("CHROMA_PERSIST_DIR", ".chroma_db"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
COLLECTION_NAME = "ampm_pos_docs"

# Categories
VALID_CATEGORIES = [
    "Verifone Hardware",
    "Buypass Config",
    "SMS Software",
    "Server Config",
    "Network / Connectivity",
    "Confirmed Fixes",
    "General"
]
