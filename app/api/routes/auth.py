import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.core.config import settings
from app.core.discord import send_access_request_notification, send_login_notification
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.models.access_request import AccessRequest
from app.schemas.auth import AccessRequestCreate, AccessRequestRead, LoginRequest, TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/access-request", response_model=AccessRequestRead, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/hour")
def request_access(request: Request, payload: AccessRequestCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(status_code=409, detail="An account already exists for this email")
    previous = db.scalar(select(AccessRequest).where(AccessRequest.email == email))
    if previous:
        if previous.locked_at:
            raise HTTPException(status_code=423, detail="This email is locked from registration")
        raise HTTPException(status_code=409, detail="An access request already exists for this email")
    invite_code = secrets.token_urlsafe(18)
    db.add(AccessRequest(email=email, invite_code_hash=hashlib.sha256(invite_code.encode()).hexdigest()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An access request already exists for this email")
    background_tasks.add_task(send_access_request_notification, email, invite_code, settings.discord_webhook_url, settings.discord_uid)
    return AccessRequestRead(message="Your request has been submitted. If approved, an invite code will be sent to your email within 1–3 business days.")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = str(payload.email).lower()
    access_request = db.scalar(select(AccessRequest).where(AccessRequest.email == email).with_for_update())
    if access_request is None:
        raise HTTPException(status_code=403, detail="Request access before registering")
    if access_request.locked_at:
        raise HTTPException(status_code=423, detail="This email is locked from registration")
    supplied_hash = hashlib.sha256(payload.invite_code.encode()).hexdigest()
    if not secrets.compare_digest(supplied_hash, access_request.invite_code_hash):
        access_request.failed_attempts += 1
        if access_request.failed_attempts >= 5:
            access_request.locked_at = datetime.now(timezone.utc)
        locked = access_request.failed_attempts >= 5
        db.commit()
        if locked:
            raise HTTPException(status_code=423, detail="Too many incorrect invite codes. This email is locked from registration.")
        remaining = 5 - access_request.failed_attempts
        raise HTTPException(status_code=400, detail=f"Incorrect invite code. {remaining} attempt(s) remaining.")
    existing = db.scalar(select(User).where(or_(User.email == payload.email.lower(), User.username == payload.username)))
    if existing:
        raise HTTPException(status_code=409, detail="Email or username is already registered")
    user = User(email=email, username=payload.username, hashed_password=hash_password(payload.password))
    db.add(user)
    db.delete(access_request)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email or username is already registered")
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password", headers={"WWW-Authenticate": "Bearer"})
    background_tasks.add_task(send_login_notification, str(payload.email), settings.discord_webhook_url, settings.discord_uid)
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserRead)
def read_me(current_user: User = Depends(get_current_user)):
    return current_user
