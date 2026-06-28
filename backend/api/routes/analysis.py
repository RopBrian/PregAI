"""API routes for fetal ultrasound image analysis"""
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from backend.config.settings import settings
from backend.database.database import get_db
from backend.database import crud
from backend.api.routes.auth import get_current_user
from backend.database.models import User, Prediction, Image, ChatMessage, Conversation
from backend.media_paths import find_gradcam_path, static_result_url, static_upload_url
from typing import Any, Optional, cast
from loguru import logger
import uuid
import os
import cv2
import numpy as np

router = APIRouter(prefix='/analysis', tags=['analysis'])
RESULTS_DIR = os.path.join('backend', 'static', 'results')
os.makedirs(RESULTS_DIR, exist_ok=True)
UPLOAD_DIR = os.path.join('backend', 'static', 'uploads')
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _get_analyzer():
    from backend.chatbot.image_analyzer import get_analyzer

    return get_analyzer()


def _build_scan_result_message(scan_name: str, prediction: str, confidence: float) -> str:
    rounded_confidence = round(float(confidence or 0))
    if prediction == 'Normal':
        return (
            f"**{scan_name}** was reviewed successfully.\n\n"
            "PregAI identified a **normal** fetal brain development pattern "
            f"with {rounded_confidence}% confidence.\n\n"
            "This can be reassuring, but it is still an educational screening result. "
            "Please share the report with your healthcare provider for clinical interpretation."
        )

    if prediction == 'Abnormal':
        return (
            f"Thank you for uploading **{scan_name}**. We've completed the AI analysis.\n\n"
            "Our screening has flagged some areas that may need attention "
            f"({rounded_confidence}% confidence). "
            "**Please don't panic** - this is a preliminary AI screening, not a diagnosis.\n\n"
            "**What this means:** This result suggests your doctor should take a closer look. "
            "Many flagged scans turn out to be perfectly fine upon professional review.\n\n"
            "**Next step:** Please discuss this result with your obstetrician or "
            "maternal-fetal medicine specialist. They have the expertise to interpret "
            "your complete medical picture.\n\n"
            "You can ask me questions about the wording or what to ask at your appointment."
        )

    return (
        f"**{scan_name}** analysis complete: {prediction} ({rounded_confidence}% confidence).\n\n"
        "Please consult with your healthcare provider for a professional interpretation."
    )


def _build_invalid_scan_message(scan_name: str, reason: str) -> str:
    return (
        f"I wasn't able to analyze **{scan_name}**.\n\n"
        f"{reason}\n\n"
        "**Tip:** Please upload a clear fetal brain ultrasound image for analysis. "
        "If you need help, just ask!"
    )


def _preview_url_from_path(path: Optional[str]) -> Optional[str]:
    return static_upload_url(path)


def _gradcam_url_for_prediction(pred: Optional[Prediction]) -> Optional[str]:
    if not pred:
        return None
    gradcam_path = find_gradcam_path(pred.image, pred)
    if gradcam_path and pred.gradcam_path != gradcam_path:
        pred.gradcam_path = gradcam_path
    return static_result_url(gradcam_path)


def _create_original_preview_from_array(image, image_id_str: str) -> Optional[str]:
    if image is None:
        return None

    preview_path = os.path.join(UPLOAD_DIR, f"{image_id_str}_preview.png")
    try:
        if len(image.shape) == 2:
            preview = image
        else:
            preview = image[:, :, :3]
        if cv2.imwrite(preview_path, preview):
            return preview_path
    except Exception as e:
        logger.warning(f"Failed to create original image preview: {e}")
    return None


def _create_original_preview_from_bytes(image_bytes: bytes, image_id_str: str) -> Optional[str]:
    try:
        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        return _create_original_preview_from_array(image, image_id_str)
    except Exception as e:
        logger.warning(f"Failed to decode original image preview: {e}")
        return None


def _ensure_original_preview(img: Image) -> Optional[str]:
    metadata = img.metadata_json or {}
    preview_path = metadata.get('original_preview_path')
    if preview_path and os.path.exists(preview_path):
        return _preview_url_from_path(preview_path)

    extension = os.path.splitext(img.file_path or '')[-1].lower()
    browser_safe_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    if extension in browser_safe_extensions and os.path.exists(img.file_path):
        return _preview_url_from_path(img.file_path)

    if not img.file_path or not os.path.exists(img.file_path):
        return None

    try:
        original = cv2.imread(img.file_path, cv2.IMREAD_COLOR)
        preview_path = _create_original_preview_from_array(original, f"image_{img.image_id}")
        if preview_path:
            img.metadata_json = {
                **metadata,
                'original_preview_path': preview_path
            }
            return _preview_url_from_path(preview_path)
    except Exception as e:
        logger.warning(f"Failed to generate preview for image {img.image_id}: {e}")
    return None


@router.post('/upload')
async def analyze_image(
    file: UploadFile = File(...),
    scan_name: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """
    Upload a fetal ultrasound image for brain analysis.
    Runs Modules A, B, and C and returns the results.
    """
    content_type = file.content_type or ''
    filename = file.filename or 'upload.png'

    if not content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail='File must be an image.')

    if not settings.enable_ml_analysis:
        raise HTTPException(
            status_code=503,
            detail='ML scan analysis is currently disabled.'
        )

    try:
        image_bytes = await file.read()
        provided_scan_name = (scan_name or '').strip()
        safe_scan_name = provided_scan_name[:80] if provided_scan_name else os.path.splitext(filename)[0][:80]
        if not safe_scan_name:
            safe_scan_name = 'Untitled scan'
        
        # Save original image
        image_id_str = str(uuid.uuid4())
        extension = filename.rsplit('.', 1)[-1] if '.' in filename else 'png'
        file_path = os.path.join(UPLOAD_DIR, f"{image_id_str}.{extension}")
        
        with open(file_path, "wb") as buffer:
            buffer.write(image_bytes)
        original_preview_path = _create_original_preview_from_bytes(image_bytes, image_id_str)

        analyzer = _get_analyzer()
        import asyncio
        result: dict[str, Any] = await asyncio.to_thread(analyzer.analyze, image_bytes)

        if result['status'] == 'error':
            raise HTTPException(status_code=500, detail=result['message'])

        db_image = None
        chat_session_id = None
        if current_user:
            if session_id:
                try:
                    chat_session_id = uuid.UUID(session_id)
                except (ValueError, TypeError):
                    chat_session_id = None

            existing_session = crud.get_conversation_session(db, chat_session_id) if chat_session_id else None
            if not existing_session or existing_session.user_id != current_user.user_id:
                existing_session = crud.create_conversation_session(db, current_user.user_id, title=f"Scan: {safe_scan_name}")
            chat_session_id = existing_session.session_id

            db_image = crud.create_image(
                db=db,
                user_id=current_user.user_id,
                file_path=file_path,
                original_filename=filename,
                format=extension,
                file_size=len(image_bytes),
                metadata_json={
                    'scan_name': safe_scan_name,
                    'result_uuid': image_id_str,
                    'original_preview_path': original_preview_path
                }
            )

        if result['status'] == 'invalid_image':
            result_message = _build_invalid_scan_message(safe_scan_name, result['message'])
            if current_user and db_image:
                # Store validation reason in image metadata for the history report
                db_image.metadata_json = {
                    **(db_image.metadata_json or {}),
                    'scan_name': safe_scan_name,
                    'module_a': result.get('module_a')
                }
                db.commit()

                if chat_session_id:
                    crud.create_chat_message(
                        db=db,
                        session_id=chat_session_id,
                        user_id=current_user.user_id,
                        role="assistant",
                        content=result_message
                    )

                crud.create_system_log(
                    db=db,
                    log_type='ML',
                    log_message=f"Image analysis rejected: {result['module_a']['prediction']} (Not a valid fetal brain scan)",
                    severity='warning',
                    user_id=current_user.user_id,
                    endpoint='/analysis/upload',
                    http_method='POST',
                    status_code=200
                )
            return {
                'result_id': image_id_str,
                'status': 'invalid_image',
                'message': result['message'],
                'module_a': result['module_a'],
                'module_b': None,
                'grad_cam_url': None,
                'original_url': _preview_url_from_path(original_preview_path) or f'/static/uploads/{os.path.basename(file_path)}',
                'scan_name': safe_scan_name,
                'session_id': str(chat_session_id) if chat_session_id else None,
                'result_message': result_message,
                'ml_context': None
            }

        grad_cam_path = None
        grad_cam_url = None

        if result.get('grad_cam_overlay') is not None:
            grad_cam_filename = f'{image_id_str}_gradcam.png'
            grad_cam_path = os.path.join(RESULTS_DIR, grad_cam_filename)
            overlay = cast(np.ndarray, result['grad_cam_overlay'])
            cv2.imwrite(grad_cam_path, cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
            grad_cam_url = f'/static/results/{grad_cam_filename}'
            del result['grad_cam_overlay']

        prediction_id = None
        if current_user and result.get('module_b') and db_image:
            db_prediction = crud.create_prediction(
                db=db,
                image_id=db_image.image_id,
                user_id=current_user.user_id,
                module_a_result=result['module_a']['prediction'],
                module_a_confidence=float(result['module_a']['confidence']),
                module_b_result=result['module_b']['prediction'],
                module_b_confidence=float(result['module_b']['confidence']),
                gradcam_path=grad_cam_path
            )
            prediction_id = db_prediction.prediction_id

        ml_context = {
            'classification': result['module_b']['prediction'] if result.get('module_b') else None,
            'confidence': result['module_b']['confidence'] if result.get('module_b') else None,
            'module_a_classification': result['module_a']['prediction'],
            'module_a_confidence': result['module_a']['confidence'],
            'grad_cam_url': grad_cam_url,
            'prediction_id': prediction_id,
            'image_id': db_image.image_id if db_image else None,
            'scan_name': safe_scan_name
        }
        result_message = _build_scan_result_message(
            safe_scan_name,
            result['module_b']['prediction'],
            result['module_b']['confidence']
        )

        if current_user and chat_session_id and prediction_id:
            crud.create_chat_message(
                db=db,
                session_id=chat_session_id,
                user_id=current_user.user_id,
                role="assistant",
                content=result_message,
                intent="ml_result_explanation",
                prediction_id=prediction_id
            )

        if current_user:
            crud.create_system_log(
                db=db,
                log_type='ML',
                log_message=f"Image analysis completed: {result['module_b']['prediction'] if result.get('module_b') else 'Invalid image'}",
                severity='info',
                user_id=current_user.user_id,
                endpoint='/analysis/upload',
                http_method='POST',
                status_code=200
            )

        return {
            'result_id': image_id_str,
            'status': 'success',
            'module_a': result['module_a'],
            'module_b': result['module_b'],
            'grad_cam_url': grad_cam_url,
            'original_url': _preview_url_from_path(original_preview_path) or f'/static/uploads/{os.path.basename(file_path)}',
            'scan_name': safe_scan_name,
            'session_id': str(chat_session_id) if chat_session_id else None,
            'result_message': result_message,
            'ml_context': ml_context,
            'chat_suggestion': 'You can ask the chatbot to explain these results by sending a message with the ml_context included.'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Image analysis failed: {e}')
        raise HTTPException(status_code=500, detail='Image analysis failed.')


@router.get('/history')
async def get_scan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve history of all scans (including rejected ones) for the authenticated user"""
    if not current_user:
        raise HTTPException(status_code=401, detail='Authentication required.')

    # Query Images joined with Predictions
    results = db.query(Image).filter(Image.user_id == current_user.user_id).order_by(Image.upload_timestamp.desc()).all()
    
    scan_history = []
    for img in results:
        original_url = _ensure_original_preview(img) or f'/static/uploads/{os.path.basename(img.file_path)}'
        if img in db.dirty:
            db.commit()

        # Check if there's an associated prediction
        pred = db.query(Prediction).filter(Prediction.image_id == img.image_id).first()
        
        if pred:
            scan_name = (img.metadata_json or {}).get('scan_name') or img.original_filename or f"Scan {img.image_id}"
            scan_history.append({
                'id': pred.prediction_id,
                'image_id': img.image_id,
                'scan_name': scan_name,
                'prediction': pred.module_b_result,
                'confidence': float(pred.module_b_confidence) if pred.module_b_confidence else 0,
                'grad_cam_url': _gradcam_url_for_prediction(pred),
                'original_url': original_url,
                'created_at': img.upload_timestamp.isoformat(),
                'status': 'success',
                'ml_context': {
                    'classification': pred.module_b_result,
                    'confidence': float(pred.module_b_confidence) if pred.module_b_confidence else None,
                    'prediction_id': pred.prediction_id,
                    'image_id': img.image_id,
                    'scan_name': scan_name,
                    'module_a': {
                        'prediction': pred.module_a_result,
                        'confidence': float(pred.module_a_confidence) if pred.module_a_confidence else None
                    }
                }
            })
            if pred in db.dirty:
                db.commit()
        else:
            scan_name = (img.metadata_json or {}).get('scan_name') or img.original_filename or f"Scan {img.image_id}"
            # This was a rejected scan or error
            scan_history.append({
                'id': f"rej_{img.image_id}",
                'image_id': img.image_id,
                'scan_name': scan_name,
                'prediction': 'Rejected',
                'confidence': 0,
                'grad_cam_url': None,
                'original_url': original_url,
                'created_at': img.upload_timestamp.isoformat(),
                'status': 'rejected',
                'message': 'Image not recognized as a valid ultrasound scan.',
                'ml_context': {
                    'image_id': img.image_id,
                    'scan_name': scan_name,
                    'module_a': img.metadata_json.get('module_a') if img.metadata_json else None
                }
            })

    return scan_history


@router.get('/result/{prediction_id}')
async def get_result_context(
    prediction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get ml_context for a specific result to use with the chatbot"""
    if not current_user:
        raise HTTPException(status_code=401, detail='Authentication required.')

    result = db.query(Prediction).filter(
        Prediction.prediction_id == prediction_id,
        Prediction.user_id == current_user.user_id
    ).first()

    if not result:
        raise HTTPException(status_code=404, detail='Result not found.')

    return {
        'ml_context': {
            'classification': result.module_b_result,
            'confidence': float(result.module_b_confidence) if result.module_b_confidence else None,
            'prediction_id': result.prediction_id,
            'image_id': result.image_id,
            'scan_name': (result.image.metadata_json or {}).get('scan_name') if result.image else None,
            'grad_cam_url': _gradcam_url_for_prediction(result)
        }
    }


@router.delete('/scan/{image_id}')
async def delete_scan(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a specific scan and its associated analysis"""
    if not current_user:
        raise HTTPException(status_code=401, detail='Authentication required.')

    img = db.query(Image).filter(
        Image.image_id == image_id,
        Image.user_id == current_user.user_id
    ).first()

    if not img:
        raise HTTPException(status_code=404, detail='Scan not found.')

    # Physical file removal
    try:
        if os.path.exists(img.file_path):
            os.remove(img.file_path)

        preview_path = (img.metadata_json or {}).get('original_preview_path')
        if preview_path and os.path.exists(preview_path) and preview_path != img.file_path:
            os.remove(preview_path)
            
        pred = db.query(Prediction).filter(Prediction.image_id == image_id).first()
        if pred and pred.gradcam_path and os.path.exists(pred.gradcam_path):
            os.remove(pred.gradcam_path)
    except Exception as e:
        logger.warning(f"Failed to delete physical files for scan {image_id}: {e}")

    pred = db.query(Prediction).filter(Prediction.image_id == image_id).first()
    if pred:
        db.query(ChatMessage).filter(
            ChatMessage.prediction_id == pred.prediction_id
        ).update(
            {ChatMessage.prediction_id: None},
            synchronize_session=False
        )
        db.query(Conversation).filter(
            Conversation.prediction_id == pred.prediction_id
        ).update(
            {Conversation.prediction_id: None},
            synchronize_session=False
        )

    db.delete(img)
    db.commit()

    crud.create_system_log(
        db=db,
        log_type='ML',
        log_message=f"User deleted scan record (ID: {image_id})",
        severity='info',
        user_id=current_user.user_id,
        endpoint=f'/analysis/scan/{image_id}',
        http_method='DELETE',
        status_code=200
    )

    return {'message': 'Scan deleted successfully.'}
