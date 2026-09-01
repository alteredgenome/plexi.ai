import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, BiometricLog
from app.schemas.biometrics import BiometricLogCreate, BiometricLogRead, CapacityEvaluationResponse
from app.api.auth import get_current_user
from app.services.integrations.ringconn import RingConnService
from app.services.scheduler import DynamicScheduler

router = APIRouter(prefix="/biometrics", tags=["Biohacking & Wearables"])

@router.get("/", response_model=List[BiometricLogRead])
async def list_biometric_logs(
    limit: int = 14,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(BiometricLog)
        .where(BiometricLog.user_id == current_user.id)
        .order_by(BiometricLog.date.desc())
        .limit(limit)
    )
    return result.scalars().all()

@router.post("/ingest", response_model=BiometricLogRead)
async def ingest_wearable_metrics(
    payload: BiometricLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests biometric data from RingConn Gen 2 Air or Pixel Watch,
    calculates recovery readiness and dynamic fatigue scaling factors.
    """
    parsed = RingConnService.parse_biometrics({
        "sleep_score": payload.sleep_score,
        "readiness_score": payload.readiness_score,
        "hrv": payload.hrv
    })

    # Check if entry exists for this date
    result = await db.execute(
        select(BiometricLog).where(
            BiometricLog.user_id == current_user.id,
            BiometricLog.date == payload.date
        )
    )
    existing = result.scalars().first()

    if existing:
        existing.sleep_score = parsed["sleep_score"]
        existing.readiness_score = parsed["readiness_score"]
        existing.hrv = parsed["hrv"]
        existing.recovery_status = parsed["recovery_status"]
        existing.fatigue_scaling_factor = parsed["fatigue_scaling_factor"]
        existing.source = payload.source
        existing.raw_data = payload.raw_data
        log_entry = existing
    else:
        log_entry = BiometricLog(
            user_id=current_user.id,
            date=payload.date,
            sleep_score=parsed["sleep_score"],
            readiness_score=parsed["readiness_score"],
            hrv=parsed["hrv"],
            recovery_status=parsed["recovery_status"],
            fatigue_scaling_factor=parsed["fatigue_scaling_factor"],
            source=payload.source,
            raw_data=payload.raw_data
        )
        db.add(log_entry)

    await db.commit()
    await db.refresh(log_entry)
    return log_entry

@router.get("/capacity-evaluation", response_model=CapacityEvaluationResponse)
async def get_daily_capacity_evaluation(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    target_date = date or datetime.date.today().isoformat()
    result = await db.execute(
        select(BiometricLog).where(
            BiometricLog.user_id == current_user.id,
            BiometricLog.date == target_date
        )
    )
    log_entry = result.scalars().first()

    if log_entry:
        fatigue_factor = log_entry.fatigue_scaling_factor
        readiness = log_entry.readiness_score or 80.0
        status = log_entry.recovery_status
    else:
        fatigue_factor = 1.0
        readiness = 80.0
        status = "moderate"

    scheduler = DynamicScheduler(
        work_start_hour=current_user.work_start_hour,
        work_end_hour=current_user.work_end_hour,
        base_capacity_minutes=current_user.daily_capacity_minutes
    )
    adjusted_cap = scheduler.calculate_adjusted_capacity(fatigue_factor)

    rec = "Standard daily output."
    if fatigue_factor < 0.8:
        rec = "Fatigue detected. Heavy analytical tasks scaled down. Focus on essential P1/P2 items."
    elif fatigue_factor > 1.1:
        rec = "High recovery peak. Excellent day for deep work blocks and high cognitive load."

    return {
        "date": target_date,
        "readiness_score": readiness,
        "recovery_status": status,
        "fatigue_scaling_factor": fatigue_factor,
        "base_capacity_minutes": current_user.daily_capacity_minutes,
        "adjusted_capacity_minutes": adjusted_cap,
        "recommendation": rec
    }
