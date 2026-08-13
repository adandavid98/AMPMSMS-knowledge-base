import os
import shutil
from pathlib import Path
from typing import List, Optional, Any, Dict
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
    history: Optional[List[Dict[str, str]]] = None


class AuthLoginRequest(BaseModel):
    auth_type: Optional[str] = None
    passphrase: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


class FeedbackRequest(BaseModel):
    question: str
    answer: str
    provider: Optional[str] = "gemini"
    feedback_type: str  # 'thumbs_up', 'thumbs_down', 'resolved'
    category: Optional[str] = "General"
    notes: Optional[str] = None



from fastapi import Header, Depends

def check_access_authorization(
    authorization: Optional[str] = Header(None),
    x_app_passphrase: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Validates authorization token or team passphrase."""
    if not config.REQUIRE_AUTH:
        return {"authenticated": True, "method": "none", "user": "Anonymous"}

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "").strip()
    elif x_app_passphrase:
        token = x_app_passphrase.strip()

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in with an @ampmservice.com email or team passphrase."
        )

    # 1. Check Team Passphrase match
    if config.APP_PASSPHRASE and token == config.APP_PASSPHRASE:
        return {"authenticated": True, "method": "passphrase", "user": "AMPM Field Technician"}

    # 2. Check Corporate Email token match
    if token.startswith("email_token_"):
        email = token.replace("email_token_", "").strip().lower()
        if email.endswith(config.ALLOWED_EMAIL_DOMAIN.lower()):
            return {"authenticated": True, "method": "email_domain", "user": email}

    # 3. Check Supabase Auth JWT Token
    if config.SUPABASE_URL and (config.SUPABASE_KEY or config.SUPABASE_SERVICE_ROLE_KEY):
        try:
            from supabase import create_client
            key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_KEY
            client = create_client(config.SUPABASE_URL, key)
            user_res = client.auth.get_user(token)
            if user_res and user_res.user:
                email = (user_res.user.email or "").lower()
                domain = config.ALLOWED_EMAIL_DOMAIN.lower()
                if email.endswith(domain):
                    return {"authenticated": True, "method": "supabase_auth", "user": email}
                else:
                    raise HTTPException(
                        status_code=403,
                        detail="Access denied. Enter a valid email."
                    )
        except HTTPException:
            raise
        except Exception:
            pass

    raise HTTPException(
        status_code=401,
        detail="Invalid authentication token or passphrase."
    )


@app.get("/")
def read_root():
    """Serves the main frontend Web UI application."""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return JSONResponse({"status": "healthy", "service": "AMPM POS Assistant API"})


@app.post("/api/auth/login")
async def login(request: AuthLoginRequest):
    """Authenticates technician using corporate email AND team passphrase."""
    email = (request.email or "").strip().lower()
    passphrase = (request.passphrase or "").strip()

    if not email:
        raise HTTPException(status_code=400, detail="Company email is required.")

    if not email.endswith(config.ALLOWED_EMAIL_DOMAIN.lower()):
        raise HTTPException(
            status_code=403,
            detail="Access denied. Enter a valid email."
        )

    if not passphrase:
        raise HTTPException(status_code=400, detail="Team passphrase is required.")

    if config.APP_PASSPHRASE and passphrase != config.APP_PASSPHRASE:
        raise HTTPException(status_code=401, detail="Invalid AMPM team passphrase.")

    return {
        "status": "success",
        "token": f"email_token_{email}",
        "user": email,
        "auth_type": "email_and_passphrase"
    }



@app.get("/api/auth/verify")
async def verify_auth_endpoint(auth_data: dict = Depends(check_access_authorization)):
    """Verifies if current session token/passphrase is valid."""
    return {
        "status": "authenticated",
        "require_auth": config.REQUIRE_AUTH,
        "auth_data": auth_data
    }


@app.get("/api/stats")
def get_stats(auth_data: dict = Depends(check_access_authorization)):
    """Returns database and vector index status."""
    coll_name = getattr(vector_store, 'collection_name', getattr(vector_store, 'table_name', 'documents'))
    doc_count = vector_store.count()
    return {
        "total_documents": doc_count,
        "total_chunks": doc_count,
        "collection_name": coll_name,
        "primary_provider": config.DEFAULT_LLM_PROVIDER,
        "status": "healthy"
    }


@app.post("/api/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    auth_data: dict = Depends(check_access_authorization)
):
    """Logs technician response feedback and indexes confirmed solutions into vectorstore."""
    user_email = auth_data.get("user", "Anonymous Technician")
    feedback_type = request.feedback_type.lower()

    # 1. Log to Supabase ticket_feedback table if configured
    if config.SUPABASE_URL and (config.SUPABASE_KEY or config.SUPABASE_SERVICE_ROLE_KEY):
        try:
            from supabase import create_client
            key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_KEY
            client = create_client(config.SUPABASE_URL, key)
            client.table("ticket_feedback").insert({
                "question": request.question,
                "answer": request.answer,
                "provider": request.provider,
                "feedback_type": feedback_type,
                "category": request.category or "General",
                "user_email": user_email,
                "notes": request.notes
            }).execute()
        except Exception as e:
            print(f"[Warning] Failed to insert feedback to Supabase: {e}")

    # 2. If technician marked "resolved" (This fixed the issue), auto-index confirmed fix into Vector Store
    indexed_as_solution = False
    if feedback_type == "resolved":
        import uuid
        fix_id = f"fix-{uuid.uuid4().hex[:8]}"
        fix_text = f"Confirmed Solution for Problem: {request.question}\n\nVerified Technician Fix:\n{request.answer}"
        fix_chunk = {
            "id": fix_id,
            "text": fix_text,
            "metadata": {
                "file_name": "Confirmed_Field_Fixes.kb",
                "category": "Confirmed Fixes",
                "topic_title": f"Verified Fix: {request.question[:60]}",
                "page_number": 1,
                "confirmed_by": user_email
            }
        }
        try:
            vector_store.add_chunks([fix_chunk])
            indexed_as_solution = True
        except Exception as e:
            print(f"[Warning] Could not ingest confirmed fix chunk: {e}")

    return {
        "status": "success",
        "feedback_type": feedback_type,
        "indexed_as_solution": indexed_as_solution,
        "message": "Thank you! Feedback recorded successfully."
    }


@app.post("/api/chat")

async def chat(
    request: ChatRequest,
    auth_data: dict = Depends(check_access_authorization),
    x_gemini_api_key: Optional[str] = Header(None, alias="X-Gemini-Api-Key"),
    x_groq_api_key: Optional[str] = Header(None, alias="X-Groq-Api-Key"),
    x_tavily_api_key: Optional[str] = Header(None, alias="X-Tavily-Api-Key")
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
            attachments=request.attachments,
            history=request.history,
            tavily_api_key=x_tavily_api_key
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest")
async def ingest_files(
    files: List[UploadFile] = File(...),
    auth_data: dict = Depends(check_access_authorization)
):
    """Uploads and ingests PDF, CHM, HTML, and TXT manuals into vector store."""

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    try:
        import tempfile
        upload_dir = Path(tempfile.gettempdir()) / "sms_ingest_temp"
        upload_dir.mkdir(parents=True, exist_ok=True)

        from ingestion import parse_document, TextChunker
        chunker = TextChunker()

        processed_files = []
        failed_files = []
        total_added_chunks = 0

        for upload_file in files:
            ext = Path(upload_file.filename).suffix.lower()
            if ext not in [".pdf", ".chm", ".html", ".htm", ".txt", ".log"]:
                continue

            file_path = upload_dir / upload_file.filename
            try:
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(upload_file.file, buffer)

                pages = parse_document(str(file_path))
                if not pages:
                    print(f"[Warning] No content parsed from {upload_file.filename}")
                    failed_files.append({"file": upload_file.filename, "reason": "No readable content found"})
                    continue

                chunks = chunker.chunk_pages(pages)
                if not chunks:
                    print(f"[Warning] No chunks generated for {upload_file.filename}")
                    failed_files.append({"file": upload_file.filename, "reason": "No text chunks generated"})
                    continue

                added = vector_store.add_chunks(chunks)
                total_added_chunks += added
                processed_files.append(upload_file.filename)

            except Exception as file_err:
                import traceback
                traceback.print_exc()
                print(f"[Error] Ingestion failed for {upload_file.filename}: {file_err}")
                failed_files.append({"file": upload_file.filename, "reason": str(file_err)})
            finally:
                if file_path.exists():
                    try:
                        file_path.unlink()
                    except Exception:
                        pass

        if not processed_files and failed_files:
            raise HTTPException(
                status_code=400,
                detail=f"Ingestion failed for {failed_files[0]['file']}: {failed_files[0]['reason']}"
            )

        return {
            "message": f"Successfully ingested {len(processed_files)} file(s).",
            "processed_files": processed_files,
            "failed_files": failed_files,
            "total_chunks": total_added_chunks,
            "current_total_chunks": vector_store.count()
        }
    except HTTPException:
        raise
    except Exception as top_err:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Server error: {str(top_err)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
