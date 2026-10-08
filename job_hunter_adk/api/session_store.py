from typing import Any
import uuid
import json
import logging

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, sessionmaker
from services.db import Base, SessionLocal, engine, get_engine

logger = logging.getLogger(__name__)

class ADKSession(Base):
    __tablename__ = 'adk_sessions'
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str] = mapped_column(Text, default="{}")

# Ensure table exists
Base.metadata.create_all(engine)

class DatabaseSessionService:
    def __init__(self, db_url: str | None = None) -> None:
        if db_url:
            self.engine = get_engine(db_url)
            self.SessionLocal = sessionmaker(bind=self.engine)
            Base.metadata.create_all(self.engine)
        else:
            self.engine = engine
            self.SessionLocal = SessionLocal
        
    def create_session(self, user_id: str) -> str:
        session_id = str(uuid.uuid4())
        with self.SessionLocal() as db:
            db_session = ADKSession(session_id=session_id, user_id=user_id)
            db.add(db_session)
            db.commit()
        return session_id
        
    def get_state(self, session_id: str) -> dict[str, Any]:
        with self.SessionLocal() as db:
            session = db.query(ADKSession).filter(ADKSession.session_id == session_id).first()
            if session and session.state:
                try:
                    return json.loads(str(session.state))
                except json.JSONDecodeError:
                    return {}
        return {}
        
    def save_state(self, session_id: str, state: dict[str, Any]) -> None:
        with self.SessionLocal() as db:
            session = db.query(ADKSession).filter(ADKSession.session_id == session_id).first()
            if session:
                session.state = json.dumps(state, default=str)
            else:
                session = ADKSession(session_id=session_id, user_id=None, state=json.dumps(state, default=str))
                db.add(session)
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
        maker = getattr(session_service, "SessionLocal", SessionLocal)
        with maker() as db:
            session = db.query(ADKSession).filter(ADKSession.session_id == session_id).first()
            if not session:
                session_id = None
                
    if not session_id:
        session_id = session_service.create_session(user_id)
        
    return session_id, user_id
