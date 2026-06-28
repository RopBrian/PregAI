from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.api.models.chat_request import ChatRequest
from backend.api.models.chat_response import ChatResponse
from backend.database.database import get_db
from backend.database import crud
from backend.api.routes.auth import get_current_user
from backend.database.models import User
from backend.media_paths import scan_result_url, static_upload_url
from loguru import logger
import uuid
from typing import Optional

router = APIRouter(prefix='/chat', tags=['chat'])


@router.post('/', response_model=ChatResponse)
async def send_message(
    request: ChatRequest, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Primary endpoint for sending a message to the PregAI chatbot.
    Saves conversation to the database and manages sessions.
    """
    try:
        from backend.chatbot.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()

        user_id = current_user.user_id if current_user else 0
        
        session_id = None
        if request.session_id:
            try:
                session_id = uuid.UUID(request.session_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid session_id format: {request.session_id}")

        response_text, intent, confidence, final_session_id = await orchestrator.chat(
            user_id=user_id,
            db=db,
            message=request.message,
            session_id=session_id,
            ml_context=request.ml_context
        )

        return ChatResponse(
            response=response_text,
            intent=intent,
            message_id=str(uuid.uuid4()),
            session_id=str(final_session_id),
            status='success'
        )

    except Exception as e:
        logger.error(f'Error in chat route: {str(e)}')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'An error occurred: {str(e)}')


@router.post('/stream')
async def stream_message(
    request: ChatRequest,
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Streaming endpoint for chat. Returns text chunks as they are generated.
    Manages its own database session to ensure it stays open during the stream.
    """
    try:
        from backend.chatbot.orchestrator import get_orchestrator
        from backend.database.database import SessionLocal
        orchestrator = get_orchestrator()

        user_id = current_user.user_id if current_user else 0
        
        session_id = None
        if request.session_id:
            try:
                session_id = uuid.UUID(request.session_id)
            except: pass

        async def generate():
            db = SessionLocal()
            try:
                async for chunk in orchestrator.stream_chat(
                    user_id=user_id,
                    message=request.message,
                    db=db,
                    session_id=session_id,
                    ml_context=request.ml_context
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield "\n\nI'm having trouble connecting to the server right now. Please try again in a moment. 💜"
            finally:
                db.close()
        
        return StreamingResponse(generate(), media_type='text/plain')
    except Exception as e:
        logger.error(f'Error in streaming chat route: {str(e)}')
        raise HTTPException(status_code=500, detail='Streaming failed.')


@router.get('/sessions')
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all chat sessions for the current user"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return crud.get_user_sessions(db, current_user.user_id)


@router.get('/sessions/{session_id}/messages')
async def get_messages(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get all messages for a specific session"""
    session = crud.get_conversation_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # Security: 
    # 1. If session belongs to a registered user, they must be that user.
    # 2. If session belongs to 0 (guest), anyone with the session_id can see it (obscurity-based).
    if session.user_id != 0:
        if not current_user or session.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this session")
    
    return crud.get_session_messages(db, session_id)


from backend.api.models.session_request import SessionRenameRequest

@router.patch('/sessions/{session_id}')
async def rename_session(
    session_id: uuid.UUID,
    request: SessionRenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a session title (user edit)"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    session = crud.get_conversation_session(db, session_id)
    if not session or session.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return crud.update_session_title(db, session_id, request.title, is_custom=True)


@router.delete('/sessions/{session_id}')
async def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Permanently delete a chat session"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    session = crud.get_conversation_session(db, session_id)
    if not session or session.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    success = crud.delete_conversation_session(db, session_id)
    return {"status": "success" if success else "failed"}


@router.get('/history')
async def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve chronological history of chat messages and scan attempts"""
    if not current_user:
        raise HTTPException(status_code=401, detail='Authentication required.')

    # 1. Get Conversation history
    from backend.database.models import Conversation, Image, Prediction
    import os

    convos = db.query(Conversation).filter(Conversation.user_id == current_user.user_id).order_by(Conversation.message_timestamp.asc()).all()
    
    # 2. Get Image history (for scans)
    images = db.query(Image).filter(Image.user_id == current_user.user_id).order_by(Image.upload_timestamp.asc()).all()

    timeline = []

    # Format conversations
    for c in convos:
        # User message
        timeline.append({
            'id': f"u_{c.conversation_id}",
            'role': 'user',
            'text': c.user_message,
            'timestamp': c.message_timestamp.isoformat(),
            'type': 'text'
        })
        # System response
        timeline.append({
            'id': f"a_{c.conversation_id}",
            'role': 'assistant',
            'text': c.system_response,
            'timestamp': c.message_timestamp.isoformat(),
            'type': 'text'
        })

    # Format images/scans
    for img in images:
        pred = db.query(Prediction).filter(Prediction.image_id == img.image_id).first()
        
        if pred:
            scan_name = (img.metadata_json or {}).get('scan_name') or img.original_filename or f"Scan {img.image_id}"
            # Successful scan
            confidence_value = float(pred.module_b_confidence) if pred.module_b_confidence is not None else 0
            timeline.append({
                'id': f"scan_{img.image_id}",
                'role': 'assistant',
                'text': f"{scan_name} analysis complete: {pred.module_b_result} ({round(confidence_value, 1)}% confidence)",
                'timestamp': img.upload_timestamp.isoformat(),
                'type': 'analysis',
                'scanName': scan_name,
                'imageUrl': scan_result_url(img, pred),
                'prediction': pred.module_b_result,
                'mlContext': {
                    'classification': pred.module_b_result,
                    'confidence': confidence_value,
                    'prediction_id': pred.prediction_id,
                    'image_id': img.image_id,
                    'scan_name': scan_name
                }
            })
        else:
            scan_name = (img.metadata_json or {}).get('scan_name') or img.original_filename or f"Scan {img.image_id}"
            # Rejected scan
            timeline.append({
                'id': f"rej_{img.image_id}",
                'role': 'assistant',
                'text': f"{scan_name} could not be analyzed. It does not appear to be a valid fetal brain ultrasound.",
                'timestamp': img.upload_timestamp.isoformat(),
                'type': 'warning',
                'scanName': scan_name,
                'imageUrl': static_upload_url(img.file_path)
            })

    # Sort everything by timestamp
    timeline.sort(key=lambda x: x['timestamp'])

    return timeline
