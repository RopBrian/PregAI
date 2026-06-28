"""Chat response schemas"""
from pydantic import BaseModel
from typing import Optional


class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    status: str = 'success'
    message_id: Optional[str] = None
    session_id: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    error_code: str