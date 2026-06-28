"""SQLAlchemy models for PregAI."""
import datetime
import uuid
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """User model for authentication and personalization."""
    __tablename__ = 'users'

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_birth: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    registration_date: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_login: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    account_status: Mapped[str] = mapped_column(String(20), default='active')
    role: Mapped[str] = mapped_column(String(20), default='pregnant_mother')
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    terms_accepted_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)

    images: Mapped[list['Image']] = relationship('Image', back_populates='user', cascade="all, delete-orphan")
    predictions: Mapped[list['Prediction']] = relationship('Prediction', back_populates='user', cascade="all, delete-orphan")
    conversations: Mapped[list['Conversation']] = relationship('Conversation', back_populates='user', cascade="all, delete-orphan")
    sessions: Mapped[list['ConversationSession']] = relationship('ConversationSession', back_populates='user', cascade="all, delete-orphan")
    logs: Mapped[list['SystemLog']] = relationship('SystemLog', back_populates='user', cascade="all, delete-orphan")


class Image(Base):
    """Stores uploaded ultrasound images."""
    __tablename__ = 'images'

    image_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    upload_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    resolution: Mapped[Optional[str]] = mapped_column(String(20))
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    storage_bucket: Mapped[Optional[str]] = mapped_column(String(100))
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship('User', back_populates='images')
    prediction: Mapped[Optional['Prediction']] = relationship(
        'Prediction',
        back_populates='image',
        uselist=False,
        cascade="all, delete-orphan",
    )


class Prediction(Base):
    """Stores metadata from Module A/B analysis."""
    __tablename__ = 'predictions'

    prediction_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    image_id: Mapped[int] = mapped_column(Integer, ForeignKey('images.image_id'), unique=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
    module_a_result: Mapped[str] = mapped_column(String(50), nullable=False)
    module_a_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    module_b_result: Mapped[Optional[str]] = mapped_column(String(50))
    module_b_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    gradcam_path: Mapped[Optional[str]] = mapped_column(String(500))
    prediction_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    processing_time: Mapped[Optional[int]] = mapped_column(Integer)
    ml_context_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    model_version: Mapped[Optional[str]] = mapped_column(String(20))
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(String(100))

    user: Mapped[User] = relationship('User', back_populates='predictions')
    image: Mapped[Image] = relationship('Image', back_populates='prediction')
    conversations: Mapped[list['Conversation']] = relationship(
        'Conversation',
        back_populates='prediction',
        cascade="all, delete-orphan",
    )


class ConversationSession(Base):
    """Groups multiple messages into a single chat session."""
    __tablename__ = 'conversation_sessions'

    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
    title: Mapped[str] = mapped_column(String(255), default="New Conversation")
    is_custom_title: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    last_message_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    user: Mapped[User] = relationship('User', back_populates='sessions')
    messages: Mapped[list['ChatMessage']] = relationship('ChatMessage', back_populates='session', cascade="all, delete-orphan")


class ChatMessage(Base):
    """Individual message turns within a session."""
    __tablename__ = 'chat_messages'

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey('conversation_sessions.session_id'))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
    prediction_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('predictions.prediction_id'), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[Optional[str]] = mapped_column(String(50))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

    session: Mapped[ConversationSession] = relationship('ConversationSession', back_populates='messages')
    prediction: Mapped[Optional[Prediction]] = relationship('Prediction')


class Conversation(Base):
    """Legacy conversation turn table still used by history/admin routes."""
    __tablename__ = 'conversations'

    conversation_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
    prediction_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('predictions.prediction_id'), nullable=True)
    message_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    intent_classified: Mapped[str] = mapped_column(String(50), nullable=False)
    intent_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    system_response: Mapped[str] = mapped_column(Text, nullable=False)
    safety_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    context_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    conversation_session: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True))
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(50))
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped[User] = relationship('User', back_populates='conversations')
    prediction: Mapped[Optional[Prediction]] = relationship('Prediction', back_populates='conversations')


class SystemLog(Base):
    """System and activity logs for auditing and debugging."""
    __tablename__ = 'system_logs'

    log_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.user_id'), nullable=True)
    log_type: Mapped[str] = mapped_column(String(50), nullable=False)
    log_message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    metadata_json: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(INET)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    endpoint: Mapped[Optional[str]] = mapped_column(String(255))
    http_method: Mapped[Optional[str]] = mapped_column(String(10))
    status_code: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped[Optional[User]] = relationship('User', back_populates='logs')
