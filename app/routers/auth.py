import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth as auth_utils, billing, email as email_utils
from app.config import settings
from app.rate_limit import login_rate_limit, register_rate_limit, forgot_password_rate_limit

router = APIRouter()


@router.post("/register", response_model=schemas.Token, dependencies=[Depends(register_rate_limit)])
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    user = models.User(
        email=payload.email,
        hashed_password=auth_utils.hash_password(payload.password),
    )
    billing.start_trial(user)

    user.email_verification_token = secrets.token_urlsafe(32)
    user.email_verification_sent_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        verify_url = f"{settings.frontend_url}/verify-email?token={user.email_verification_token}"
        email_utils.send_verification_email(user.email, verify_url)
    except email_utils.EmailNotConfiguredError:
        pass

    token = auth_utils.create_access_token(user.id)
    return schemas.Token(access_token=token)


@router.post("/login", response_model=schemas.Token, dependencies=[Depends(login_rate_limit)])
def login(payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not auth_utils.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    token = auth_utils.create_access_token(user.id)
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(auth_utils.get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=schemas.MessageOut, dependencies=[Depends(forgot_password_rate_limit)])
def forgot_password(payload: schemas.ForgotPasswordRequest, db: Session = Depends(get_db)):
    generic_response = schemas.MessageOut(message="If that email has an account, a reset link is on its way.")

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return generic_response

    user.password_reset_token = secrets.token_urlsafe(32)
    user.password_reset_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    try:
        reset_url = f"{settings.frontend_url}/reset-password?token={user.password_reset_token}"
        email_utils.send_password_reset_email(user.email, reset_url)
    except email_utils.EmailNotConfiguredError:
        pass

    return generic_response


@router.post("/reset-password", response_model=schemas.MessageOut)
def reset_password(payload: schemas.ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.password_reset_token == payload.token).first()

    if not user or not user.password_reset_expires_at or datetime.utcnow() > user.password_reset_expires_at:
        raise HTTPException(400, "This reset link is invalid or has expired — request a new one.")

    if len(payload.new_password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters.")

    user.hashed_password = auth_utils.hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_expires_at = None
    db.commit()

    return schemas.MessageOut(message="Password updated. You can sign in with your new password now.")


@router.post("/verify-email", response_model=schemas.MessageOut)
def verify_email(payload: schemas.VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email_verification_token == payload.token).first()
    if not user:
        raise HTTPException(400, "Invalid or already-used verification link.")

    user.email_verified = True
    user.email_verification_token = None
    db.commit()

    return schemas.MessageOut(message="Email verified.")


@router.post("/resend-verification", response_model=schemas.MessageOut)
def resend_verification(
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.email_verified:
        return schemas.MessageOut(message="Your email is already verified.")

    current_user.email_verification_token = secrets.token_urlsafe(32)
    current_user.email_verification_sent_at = datetime.utcnow()
    db.commit()

    try:
        verify_url = f"{settings.frontend_url}/verify-email?token={current_user.email_verification_token}"
        email_utils.send_verification_email(current_user.email, verify_url)
    except email_utils.EmailNotConfiguredError as e:
        raise HTTPException(501, str(e))

    return schemas.MessageOut(message="Verification email sent.")
