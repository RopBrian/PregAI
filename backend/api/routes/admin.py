from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from backend.database.database import get_db
from backend.database import crud, models
from backend.api.routes.auth import get_current_user

router = APIRouter(prefix='/admin', tags=['admin'])

def is_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != 'system_admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted for this user role."
        )
    return current_user

@router.get('/stats')
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    admin: models.User = Depends(is_admin)
):
    from datetime import datetime
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = db.query(func.count(models.User.user_id)).scalar()

    # Total uploads overall and for today
    total_scans = db.query(func.count(models.Image.image_id)).scalar()
    scans_today = db.query(func.count(models.Image.image_id)).filter(models.Image.upload_timestamp >= today_start).scalar()

    # Validated vs Rejected breakdown: provide both today's and total counts
    validated_today = db.query(func.count(models.Prediction.prediction_id)).filter(models.Prediction.prediction_timestamp >= today_start).scalar()
    validated_total = db.query(func.count(models.Prediction.prediction_id)).scalar()

    rejected_today = scans_today - validated_today if scans_today > validated_today else 0
    rejected_total = total_scans - validated_total if total_scans > validated_total else 0

    # Predictions counts (today + total)
    predictions_today = validated_today
    total_predictions = validated_total

    # Safety alerts count today (keep as today-focused for now)
    safety_alerts = db.query(func.count(models.Conversation.conversation_id)).filter(
        models.Conversation.safety_flag == True,
        models.Conversation.message_timestamp >= today_start
    ).scalar() or 0

    return {
        "totalUsers": total_users,
        "activeAlerts": safety_alerts,
        "systemStatus": "Optimal",
        "scansToday": scans_today,
        "totalScans": total_scans,
        "validatedToday": validated_today,
        "validatedTotal": validated_total,
        "rejectedToday": rejected_today,
        "rejectedTotal": rejected_total,
        "predictionsToday": predictions_today,
        "totalPredictions": total_predictions
    }

@router.get('/logs', response_model=List[dict])
async def get_recent_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: models.User = Depends(is_admin)
):
    """Retrieve detailed system logs for the audit trail"""
    logs = crud.get_system_logs(db, limit=limit)
    return [
        {
            "id": log.log_id,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "level": log.severity,
            "module": log.log_type,
            "user": log.user.username if log.user else "System",
            "activity": log.log_message,
            "ip": log.ip_address or "N/A"
        }
        for log in logs
    ]
