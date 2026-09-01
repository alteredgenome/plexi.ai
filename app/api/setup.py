import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, SystemSetting, Calendar, Household, HouseholdMember, IntegrationCredential
from app.schemas.setup import SetupStatus, SetupWizardRequest, SetupWizardResponse
from app.core.security import hash_password, create_access_token
from app.config import settings

router = APIRouter(prefix="/setup", tags=["First-Run Setup Wizard"])

@router.get("/status", response_model=SetupStatus)
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    """
    Returns whether the Plexi instance is already configured or requires first-run setup wizard.
    """
    setting_res = await db.execute(select(SystemSetting).where(SystemSetting.key == "setup_completed"))
    setting = setting_res.scalars().first()

    user_count_res = await db.execute(select(User))
    users = user_count_res.scalars().all()

    is_completed = (setting is not None and setting.value == "true") or len(users) > 0

    return {
        "is_setup_completed": is_completed,
        "instance_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "admin_exists": len(users) > 0
    }

@router.post("/initialize", response_model=SetupWizardResponse)
async def run_setup_wizard(payload: SetupWizardRequest, db: AsyncSession = Depends(get_db)):
    """
    Initializes the Plexi instance on first access:
    - Creates root Admin account
    - Sets default Calendar & Household
    - Configures OpenRouter, Home Assistant, and Pavlok credentials
    - Locks setup to prevent re-initialization
    """
    # Check if an admin user already exists
    user_count_res = await db.execute(select(User))
    if len(user_count_res.scalars().all()) > 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plexi instance is already configured. Please log in."
        )

    # 1. Create Admin User
    admin = User(
        email=payload.admin_email.strip().lower(),
        hashed_password=hash_password(payload.admin_password),
        full_name=payload.admin_name.strip(),
        is_admin=True,
        timezone=payload.timezone,
        work_start_hour=payload.work_start_hour,
        work_end_hour=payload.work_end_hour,
        daily_capacity_minutes=payload.daily_capacity_minutes
    )
    db.add(admin)
    await db.flush()

    # 2. Create Default Calendar
    default_cal = Calendar(
        user_id=admin.id,
        name="Executive Primary",
        color="#4F46E5",
        visibility="full",
        is_default=True
    )
    db.add(default_cal)

    # 3. Create Default Household
    hh = Household(name=f"{admin.full_name}'s Household")
    db.add(hh)
    await db.flush()

    member = HouseholdMember(household_id=hh.id, user_id=admin.id, role="admin")
    db.add(member)

    # 4. Store Optional Integration Credentials
    if payload.openrouter_api_key and payload.openrouter_api_key.strip():
        db.add(IntegrationCredential(
            user_id=admin.id,
            provider="openrouter",
            credentials_json={"api_key": payload.openrouter_api_key.strip(), "model": payload.openrouter_model or "google/gemma-2-9b-it:free"}
        ))

    if payload.home_assistant_token and payload.home_assistant_token.strip():
        db.add(IntegrationCredential(
            user_id=admin.id,
            provider="home_assistant",
            credentials_json={"base_url": payload.home_assistant_url or "http://homeassistant.local:8123", "token": payload.home_assistant_token.strip()}
        ))

    if payload.pavlok_api_key and payload.pavlok_api_key.strip():
        db.add(IntegrationCredential(
            user_id=admin.id,
            provider="pavlok",
            credentials_json={"api_key": payload.pavlok_api_key.strip()}
        ))

    # 5. Lock Setup
    db.add(SystemSetting(key="setup_completed", value="true"))
    await db.commit()
    await db.refresh(admin)

    token = create_access_token(data={"sub": str(admin.id), "email": admin.email, "is_admin": True})

    return {
        "status": "success",
        "message": "Plexi instance initialized successfully!",
        "access_token": token,
        "user_id": admin.id,
        "redirect_url": "/"
    }
