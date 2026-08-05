import os
import shutil
from pathlib import Path
from typing import List, Optional, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ingestion import PDFParser, TextChunker
from vectorstore import VectorStoreManager
from rag import RAGEngine
import config

app = FastAPI(
    title="AMPM Service POS Troubleshooting API",
    version="2.0.0",
    description="RAG-powered REST API for POS Field Technical Support"
)

# Initialize RAG Engine and Vector Store
vector_store = VectorStoreManager()
rag_engine = RAGEngine(vector_store=vector_store)

# Mount Static Files
static_dir = Path(__file__).parent / "static"
# Enable CORS for cross-origin web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve root static assets (css, js, images, static)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("css"):
    app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("js"):
    app.mount("/js", StaticFiles(directory="js"), name="js")
if os.path.exists("images"):
    app.mount("/images", StaticFiles(directory="images"), name="images")


class ChatRequest(BaseModel):
    question: str
    provider: Optional[str] = config.DEFAULT_LLM_PROVIDER
    category: Optional[str] = None
    top_k: Optional[int] = 5
    images: Optional[List[Any]] = None
    attachments: Optional[List[Any]] = None


@app.get("/")
def read_root():
    """Serves the main frontend Web UI application."""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return JSONResponse({"status": "healthy", "service": "AMPM POS Assistant API"})


@app.get("/api/stats")
def get_stats():
    """Returns database and vector index status."""
    coll_name = getattr(vector_store, 'collection_name', getattr(vector_store, 'table_name', 'documents'))
    return {
        "total_documents": vector_store.count(),
        "collection_name": coll_name,
        "primary_provider": config.DEFAULT_LLM_PROVIDER,
        "status": "healthy"
    }


from fastapi import FastAPI, UploadFile, File, HTTPException, Header

@app.post("/api/chat")
async def chat(
    request: ChatRequest,
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key"),
    x_groq_api_key: Optional[str] = Header(None, alias="X-Groq-Api-Key")
):
    """Processes technician question through RAG pipeline and returns cited answer."""
    if not request.question.strip() and not request.images and not request.attachments:
        raise HTTPException(status_code=400, detail="Question or attachments cannot be empty.")

    provider = (request.provider or config.DEFAULT_LLM_PROVIDER).lower()
    custom_api_key = None

    if provider == "gemini" and x_gemini_api_key:
        custom_api_key = x_gemini_api_key
    elif provider == "groq" and x_groq_api_key:
        custom_api_key = x_groq_api_key

    try:
        result = rag_engine.query(
            question=request.question or "Analyze attached image/document for POS troubleshooting.",
            provider_name=request.provider,
            top_k=request.top_k,
            category=request.category,
            api_key=custom_api_key,
            images=request.images,
            attachments=request.attachments
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest")
async def ingest_files(files: List[UploadFile] = File(...)):
    """Uploads and ingests PDF and CHM manuals into vector store."""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    upload_dir = Path(__file__).parent / "sample_docs"
    upload_dir.mkdir(exist_ok=True)

    from ingestion import parse_document, TextChunker
    chunker = TextChunker()

    processed_files = []
    total_added_chunks = 0

    for upload_file in files:
        ext = Path(upload_file.filename).suffix.lower()
        if ext not in [".pdf", ".chm"]:
            continue

        file_path = upload_dir / upload_file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

        pages = parse_document(str(file_path))
        chunks = chunker.chunk_pages(pages)
        added = vector_store.add_chunks(chunks)
        
        total_added_chunks += added
        processed_files.append(upload_file.filename)

    return {
        "message": f"Successfully ingested {len(processed_files)} file(s).",
        "processed_files": processed_files,
        "total_chunks": total_added_chunks,
        "current_total_chunks": vector_store.count()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
