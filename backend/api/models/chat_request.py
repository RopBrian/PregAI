"""Chat request schemas"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = 'anonymous'
    session_id: Optional[str] = None
    ml_context: Optional[Dict[str, Any]] = None


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int
    comment: Optional[str] = None