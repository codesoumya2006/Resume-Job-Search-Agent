import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from api.deps import verify_api_key
from api.schemas import SessionRequest, SessionResponse, ChatRequest, ChatResponse
from api.session_store import DatabaseSessionService, get_or_create_session
from agent import root_agent

import logging
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

logger = logging.getLogger(__name__)

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
adk_session_service = InMemorySessionService()

runner = Runner(
    agent=root_agent,
    session_service=adk_session_service,
    app_name="job_hunter_adk",
    auto_create_session=True,
)

@app.get("/health", dependencies=[Depends(verify_api_key)])
def health_check() -> dict[str, str]:
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
def create_session(request: SessionRequest | None = None) -> SessionResponse:
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
def upload_resume(file: UploadFile = File(...)) -> dict[str, str]:
    """
    Parses a PDF, DOCX, or TXT file and returns the extracted text.
    Rejects corrupt, empty, unextractable, or unsupported files with controlled HTTP 400 responses.
    Never fabricates resume data and never exposes internal traces or secrets.
    """
    name = (file.filename or "").lower()
    if not name:
        raise HTTPException(status_code=400, detail="Missing filename in upload.")
        
    try:
        content = file.file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read uploaded file data.") from None
        
    if not content or len(content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
        
    if name.endswith(".txt"):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception:
                raise HTTPException(status_code=400, detail="Corrupt or invalid text file encoding.") from None
        if not text.strip():
            raise HTTPException(status_code=400, detail="The uploaded text file is empty.")
        return {"text": text}
        
    elif name.endswith(".pdf"):
        import io
        try:
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(content))
            except ImportError:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                
            extracted_pages = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
            text = "\n".join(extracted_pages)
            if not text.strip():
                raise HTTPException(status_code=400, detail="The uploaded PDF contains no extractable text.")
            return {"text": text}
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("PDF extraction failed: %s", type(e).__name__)
            raise HTTPException(status_code=400, detail="Corrupt or invalid PDF file.") from None
            
    elif name.endswith(".docx"):
        import io
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
            paragraphs = [para.text for para in doc.paragraphs if para.text]
            text = "\n".join(paragraphs)
            if not text.strip():
                raise HTTPException(status_code=400, detail="The uploaded DOCX contains no extractable text.")
            return {"text": text}
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("DOCX extraction failed: %s", type(e).__name__)
            raise HTTPException(status_code=400, detail="Corrupt or invalid DOCX file.") from None
            
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a PDF, DOCX, or TXT file.")

@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest) -> ChatResponse:
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
    
    # Establish explicit HITL confirmation: True if explicitly confirmed, False otherwise.
    # Missing field safely behaves as unconfirmed (False). user_confirmed=False remains False.
    if request.user_confirmed is not None:
        user_confirmed = request.user_confirmed
    elif request.state_updates and "user_confirmed" in request.state_updates:
        user_confirmed = bool(request.state_updates["user_confirmed"])
    else:
        user_confirmed = False
    
    state["user_confirmed"] = user_confirmed

    draft = state.get("email_draft")
    msg_lower = request.message.strip().lower()
    is_send_action = bool(draft) and (
        any(kw in msg_lower for kw in ["send", "submit", "apply", "approve"])
        or (request.user_confirmed is True)
    )

    if is_send_action:
        from sub_agents.application_agent.tools import _send_email_impl
        send_res = _send_email_impl(draft, user_confirmed=user_confirmed)
        if user_confirmed and send_res.get("status") == "sent":
            draft["status"] = "sent"
            state["email_draft"] = draft
            state["application_status"] = "sent"
            response_text = "Application email sent successfully."
        else:
            draft["status"] = "pending_user_approval"
            state["email_draft"] = draft
            state["application_status"] = "refused_unconfirmed"
            response_text = f"Application refused: {send_res.get('reason', 'awaiting explicit user confirmation')}."
        new_state = state
    else:
        # Real Google ADK Runner execution
        try:
            # Synchronize state into ADK session
            adk_sess = await adk_session_service.get_session(
                app_name="job_hunter_adk", user_id=user_id, session_id=session_id
            )
            if not adk_sess:
                adk_sess = await adk_session_service.create_session(
                    app_name="job_hunter_adk", user_id=user_id, session_id=session_id, state=state
                )
            else:
                adk_sess.state.update(state)

            new_message = types.Content(
                role="user",
                parts=[types.Part.from_text(text=request.message)]
            )

            response_text = ""
            async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=new_message):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text

            if not response_text:
                response_text = "Turn completed."

            # Synchronize state back from ADK session
            fresh_adk_sess = await adk_session_service.get_session(
                app_name="job_hunter_adk", user_id=user_id, session_id=session_id
            )
            target_sess = fresh_adk_sess or adk_sess
            if target_sess and target_sess.state:
                state.update(target_sess.state)
            new_state = state
        except Exception as e:
            logger.error("ADK Runner execution error: %s", e, exc_info=True)
            response_text = "The agent encountered an error processing your request. Please try again."
            new_state = state
            
    session_service.save_state(session_id, new_state)
    
    state_snapshot = {
        "resume_profile": new_state.get("resume_profile"),
        "discovered_jobs": new_state.get("discovered_jobs"),
        "ranked_jobs": new_state.get("ranked_jobs"),
        "selected_job": new_state.get("selected_job"),
        "company_intel": new_state.get("company_intel"),
        "interview_prep": new_state.get("interview_prep") or new_state.get("interview_results"),
        "email_draft": new_state.get("email_draft"),
        "user_confirmed": new_state.get("user_confirmed", False),
        "application_status": new_state.get("application_status")
    }
    
    return ChatResponse(
        session_id=session_id,
        user=user_id,
        response=response_text,
        state_snapshot=state_snapshot
    )

os.makedirs("ui/web", exist_ok=True)
app.mount("/", StaticFiles(directory="ui/web", html=True), name="static")
