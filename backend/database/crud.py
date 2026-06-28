"""CRUD operations for users, images, predictions, and conversations in PregAI"""
from sqlalchemy.orm import Session
from backend.database import models
from backend.media_paths import scan_result_url
from typing import List, Optional
import uuid
import datetime


def get_user(db: Session, user_id: int) -> Optional[models.User]:
    """Get user by ID"""
    return db.query(models.User).filter(models.User.user_id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Get user by username"""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Get user by email"""
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, username: str, email: str, password_hash: str, role: str = 'pregnant_mother', terms_accepted: bool = False) -> models.User:
    """Create a new user"""
    db_user = models.User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        terms_accepted=terms_accepted,
        terms_accepted_at=datetime.datetime.utcnow() if terms_accepted else None
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def create_image(
    db: Session,
    user_id: int,
    file_path: str,
    original_filename: str,
    format: str,
    file_size: Optional[int] = None,
    resolution: Optional[str] = None,
    metadata_json: Optional[dict] = None
) -> models.Image:
    """Register an uploaded image"""
    db_image = models.Image(
        user_id=user_id,
        file_path=file_path,
        original_filename=original_filename,
        format=format,
        file_size=file_size,
        resolution=resolution,
        metadata_json=metadata_json
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)
    return db_image


def create_prediction(
    db: Session,
    image_id: int,
    user_id: int,
    module_a_result: str,
    module_a_confidence: float,
    module_b_result: Optional[str] = None,
    module_b_confidence: Optional[float] = None,
    gradcam_path: Optional[str] = None,
    processing_time: Optional[int] = None,
    ml_context_json: Optional[dict] = None,
    model_version: Optional[str] = None
) -> models.Prediction:
    """Create a new prediction record"""
    db_prediction = models.Prediction(
        image_id=image_id,
        user_id=user_id,
        module_a_result=module_a_result,
        module_a_confidence=module_a_confidence,
        module_b_result=module_b_result,
        module_b_confidence=module_b_confidence,
        gradcam_path=gradcam_path,
        processing_time=processing_time,
        ml_context_json=ml_context_json,
        model_version=model_version
    )
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction


def get_predictions_by_user(db: Session, user_id: int) -> List[models.Prediction]:
    """Get all predictions for a user"""
    return (
        db.query(models.Prediction)
        .filter(models.Prediction.user_id == user_id)
        .order_by(models.Prediction.prediction_timestamp.desc())
        .all()
    )


def create_conversation_session(db: Session, user_id: int, title: str = "New Conversation") -> models.ConversationSession:
    """Create a new chat session"""
    db_session = models.ConversationSession(
        user_id=user_id,
        title=title
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_conversation_session(db: Session, session_id: uuid.UUID) -> Optional[models.ConversationSession]:
    """Get a specific chat session by UUID"""
    return db.query(models.ConversationSession).filter(models.ConversationSession.session_id == session_id).first()


def update_session_title(db: Session, session_id: uuid.UUID, title: str, is_custom: bool = True) -> Optional[models.ConversationSession]:
    """Update session title and mark as custom if edited by user"""
    db_session = get_conversation_session(db, session_id)
    if db_session:
        db_session.title = title
        db_session.is_custom_title = is_custom
        db_session.last_message_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(db_session)
    return db_session


def delete_conversation_session(db: Session, session_id: uuid.UUID) -> bool:
    """Delete a chat session and all its messages"""
    # Explicitly delete messages first using a query
    db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id).delete(synchronize_session=False)
    
    db_session = get_conversation_session(db, session_id)
    if db_session:
        db.delete(db_session)
        db.commit()
        return True
    db.commit() # Commit message deletion anyway
    return False


def get_user_sessions(db: Session, user_id: int, limit: int = 20) -> List[models.ConversationSession]:
    """Get recent chat sessions for a user"""
    return (
        db.query(models.ConversationSession)
        .filter(models.ConversationSession.user_id == user_id)
        .order_by(models.ConversationSession.last_message_at.desc())
        .limit(limit)
        .all()
    )


def create_chat_message(
    db: Session,
    session_id: uuid.UUID,
    user_id: int,
    role: str,
    content: str,
    intent: Optional[str] = None,
    prediction_id: Optional[int] = None
) -> models.ChatMessage:
    """Add a message to a session"""
    db_message = models.ChatMessage(
        session_id=session_id,
        user_id=user_id,
        role=role,
        content=content,
        intent=intent,
        prediction_id=prediction_id
    )
    db.add(db_message)
    
    # Update last_message_at in session
    db_session = get_conversation_session(db, session_id)
    if db_session:
        db_session.last_message_at = datetime.datetime.utcnow()
        
    db.commit()
    db.refresh(db_message)
    return db_message


def get_session_messages(db: Session, session_id: uuid.UUID, limit: int = 50) -> List[dict]:
    """Get all messages for a session including prediction media if available"""
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.session_id == session_id)
        .order_by(models.ChatMessage.timestamp.asc())
        .limit(limit)
        .all()
    )
    
    # Enrich with prediction media
    results = []
    for msg in messages:
        msg_dict = {
            "message_id": msg.message_id,
            "session_id": str(msg.session_id),
            "user_id": msg.user_id,
            "role": msg.role,
            "content": msg.content,
            "intent": msg.intent,
            "timestamp": msg.timestamp.isoformat(),
            "prediction_id": msg.prediction_id,
            "imageUrl": None,
            "type": None
        }
        
        if msg.prediction_id:
            pred = db.query(models.Prediction).filter(models.Prediction.prediction_id == msg.prediction_id).first()
            if pred:
                msg_dict["type"] = "analysis"
                scan_name = (pred.image.metadata_json or {}).get('scan_name') if pred.image else None
                msg_dict["scanName"] = scan_name or (pred.image.original_filename if pred.image else None) or f"Scan {pred.image_id}"
                msg_dict["mlContext"] = {
                    "classification": pred.module_b_result,
                    "confidence": float(pred.module_b_confidence) if pred.module_b_confidence else None,
                    "prediction_id": pred.prediction_id,
                    "image_id": pred.image_id,
                    "scan_name": msg_dict["scanName"],
                    "module_a_classification": pred.module_a_result,
                    "module_a_confidence": float(pred.module_a_confidence) if pred.module_a_confidence else None
                }
                msg_dict["imageUrl"] = scan_result_url(pred.image, pred)
        
        results.append(msg_dict)
        
    return results


def create_conversation_message(
    db: Session,
    user_id: int,
    user_message: str,
    intent_classified: str,
    intent_confidence: float,
    system_response: str,
    prediction_id: Optional[int] = None,
    conversation_session: Optional[uuid.UUID] = None,
    context_json: Optional[dict] = None
) -> models.Conversation:
    """Legacy: Create a new conversation entry in the flat table"""
    db_convo = models.Conversation(
        user_id=user_id,
        prediction_id=prediction_id,
        user_message=user_message,
        intent_classified=intent_classified,
        intent_confidence=intent_confidence,
        system_response=system_response,
        conversation_session=conversation_session,
        context_json=context_json
    )
    db.add(db_convo)
    db.commit()
    db.refresh(db_convo)
    return db_convo


def get_conversation_history(db: Session, user_id: int, limit: int = 50) -> List[models.Conversation]:
    """Legacy: Get conversation history for a user from the flat table"""
    return (
        db.query(models.Conversation)
        .filter(models.Conversation.user_id == user_id)
        .order_by(models.Conversation.message_timestamp.asc())
        .limit(limit)
        .all()
    )


def create_system_log(
    db: Session,
    log_type: str,
    log_message: str,
    severity: str,
    user_id: Optional[int] = None,
    metadata_json: Optional[dict] = None,
    endpoint: Optional[str] = None,
    http_method: Optional[str] = None,
    status_code: Optional[int] = None
) -> models.SystemLog:
    """Create a system log entry"""
    db_log = models.SystemLog(
        user_id=user_id,
        log_type=log_type,
        log_message=log_message,
        severity=severity,
        metadata_json=metadata_json,
        endpoint=endpoint,
        http_method=http_method,
        status_code=status_code
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def get_system_logs(db: Session, limit: int = 100) -> List[models.SystemLog]:
    """Get recent system logs"""
    return (
        db.query(models.SystemLog)
        .order_by(models.SystemLog.timestamp.desc())
        .limit(limit)
        .all()
    )
