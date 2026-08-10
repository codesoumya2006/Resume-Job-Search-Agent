import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.deps import verify_api_key
from api.schemas import SessionRequest, SessionResponse, ChatRequest, ChatResponse
from api.session_store import DatabaseSessionService, get_or_create_session
from agent import root_agent

try:
    from google.adk.runner import Runner
except ImportError:
    # Use our mock runner if ADK is missing
    from main import Runner

app = FastAPI(title="Job Hunter API")

# Configure CORS
origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [origin.strip() for origin in origins_env.split(",")] if origins_env else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = DatabaseSessionService()

@app.get("/health", dependencies=[Depends(verify_api_key)])
def health_check():
    """
    Health check that verifies API key and checks DB connectivity.
    """
    status = "ok"
    try:
        from services.db import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        status = "degraded"
        
    return {
        "status": status,
        "app_name": "job_hunter_adk",
        "session_backend": "database"
    }

@app.post("/session", response_model=SessionResponse, dependencies=[Depends(verify_api_key)])
def create_session(request: SessionRequest | None = None):
    """
    Auto-creates a session and user if omitted.
    """
    req = request or SessionRequest()
    session_id, user_id = get_or_create_session(session_service, None, req.user_id)
    return SessionResponse(
        user_id=user_id,
        session_id=session_id,
        app_name="job_hunter_adk"
    )

@app.post("/upload", dependencies=[Depends(verify_api_key)])
def upload_resume(file: UploadFile = File(...)):
    """
    Parses a PDF, DOCX, or TXT file and returns the extracted text.
    """
    name = (file.filename or "").lower()
    content = file.file.read()
    
    if name.endswith(".txt"):
        return {"text": content.decode("utf-8", errors="ignore")}
    elif name.endswith(".pdf"):
        try:
            import PyPDF2
            import io
            reader = PyPDF2.PdfReader(io.BytesIO(content))
            text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
            return {"text": text}
        except ImportError:
            return {"error": "PyPDF2 is required for PDF parsing."}
    elif name.endswith(".docx"):
        try:
            import docx
            import io
            doc = docx.Document(io.BytesIO(content))
            text = "\n".join(para.text for para in doc.paragraphs)
            return {"text": text}
        except ImportError:
            return {"error": "python-docx is required for DOCX parsing."}
    else:
        return {"error": "Unsupported file type."}

@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
def chat(request: ChatRequest):
    """
    Runs the agent against the provided session (or creates one).
    Returns the agent's response and state snapshot.
    """
    session_id, user_id = get_or_create_session(session_service, request.session_id, request.user)
    
    # Get current state
    state = session_service.get_state(session_id)
    
    # Apply any initial state updates (like preferences or parsed resume)
    if request.state_updates:
        state.update(request.state_updates)
    
    # Initialize Runner
    runner = Runner(agent=root_agent, session_service=session_service)
    
    try:
        result = runner.run(request.message, state=state)
    except TypeError:
        result = runner.run(request.message)
        
    if isinstance(result, dict):
        response_text = result.get("response", "")
        new_state = result.get("state", state)
    else:
        response_text = str(result)
        new_state = state
        
    session_service.save_state(session_id, new_state)
    
    state_snapshot = {
        "ranked_jobs": new_state.get("ranked_jobs"),
        "company_intel": new_state.get("company_intel"),
        "email_draft": new_state.get("email_draft")
    }
    
    return ChatResponse(
        session_id=session_id,
        user=user_id,
        response=response_text,
        state_snapshot=state_snapshot
    )

os.makedirs("ui/web", exist_ok=True)
app.mount("/", StaticFiles(directory="ui/web", html=True), name="static")
