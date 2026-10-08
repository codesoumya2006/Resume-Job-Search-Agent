from typing import Any, Optional
from pydantic import BaseModel

class SessionRequest(BaseModel):
    user_id: Optional[str] = None

class SessionResponse(BaseModel):
    user_id: str
    session_id: str
    app_name: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user: Optional[str] = None
    message: str
    state_updates: Optional[dict[str, Any]] = None
    user_confirmed: Optional[bool] = None

class ChatResponse(BaseModel):
    session_id: str
    user: str
    response: str
    state_snapshot: Optional[dict[str, Any]] = None
