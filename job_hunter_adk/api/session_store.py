import uuid
import json
import logging

logger = logging.getLogger(__name__)

try:
    from google.adk.services import DatabaseSessionService
except ImportError:
    logger.info("google.adk.services.DatabaseSessionService not found, using robust fallback.")
    from sqlalchemy import Column, String, Text
    from services.db import Base, SessionLocal, engine

    class ADKSession(Base):
        __tablename__ = 'adk_sessions'
        session_id = Column(String, primary_key=True)
        user_id = Column(String)
        state = Column(Text, default="{}")

    # Ensure table exists
    Base.metadata.create_all(engine)

    class DatabaseSessionService:
        def __init__(self, db_url=None):
            # We ignore db_url because we are using the globally configured engine from services.db
            pass
            
        def create_session(self, user_id: str) -> str:
            session_id = str(uuid.uuid4())
            with SessionLocal() as db:
                db_session = ADKSession(session_id=session_id, user_id=user_id)
                db.add(db_session)
                db.commit()
            return session_id
            
        def get_state(self, session_id: str) -> dict:
            with SessionLocal() as db:
                session = db.query(ADKSession).filter(ADKSession.session_id == session_id).first()
                if session and session.state:
                    try:
                        return json.loads(session.state)
                    except json.JSONDecodeError:
                        return {}
            return {}
            
        def save_state(self, session_id: str, state: dict):
            with SessionLocal() as db:
                session = db.query(ADKSession).filter(ADKSession.session_id == session_id).first()
                if session:
                    session.state = json.dumps(state)
                    db.commit()

def get_or_create_session(session_service: DatabaseSessionService, session_id: str | None, user_id: str | None) -> tuple[str, str]:
    """
    Looks up or creates a session.
    If session_id is None, it creates a new one.
    If session_id is provided, it tries to use it. If not found, creates a new one.
    Returns (session_id, user_id).
    """
    if not user_id:
        user_id = "user-" + uuid.uuid4().hex[:8]
        
    if session_id:
        # Check if session exists in DB
        with SessionLocal() as db:
            session = db.query(ADKSession).filter(ADKSession.session_id == session_id).first()
            if not session:
                session_id = None
                
    if not session_id:
        session_id = session_service.create_session(user_id)
        
    return session_id, user_id
