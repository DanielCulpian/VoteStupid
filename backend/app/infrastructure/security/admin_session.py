import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.infrastructure.models.admin_session_model import AdminSessionModel
from app.infrastructure.security.api_protection import allowed_origins

COOKIE_NAME = "votestupid_admin"


def password_hash(password: str, salt: str | None = None) -> str:
    """Calculate scrypt with a random salt without retaining the original password."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=32768, r=8, p=3,
                            maxmem=64 * 1024 * 1024, dklen=32).hex()
    return f"scrypt${salt}${digest}"


def credential_version() -> str:
    """Identify the credential configuration to invalidate sessions after a password change."""
    return hashlib.sha256(os.getenv("ADMIN_PASSWORD_HASH", "").encode()).hexdigest()


def verify_password(password: str) -> bool:
    """Verify the configured hash and fail closed when it is missing or malformed."""
    configured = os.getenv("ADMIN_PASSWORD_HASH", "")
    if not re.fullmatch(r"scrypt\$[0-9a-f]{32}\$[0-9a-f]{64}", configured):
        raise HTTPException(503, "El acceso privado no está configurado. Contacta con el administrador.")
    return hmac.compare_digest(password_hash(password, configured.split("$")[1]), configured)


def session_hash(token: str) -> str:
    """Derive the lookup key without storing the cookie secret."""
    return hashlib.sha256(token.encode()).hexdigest()


def secure_cookie() -> bool:
    """Keep Secure enabled unless local HTTP development is explicitly allowed."""
    return os.getenv("ADMIN_COOKIE_SECURE", "true").lower() != "false"


def protect_admin_request(request: Request):
    """Require a non-simple header and an authorized origin for administrative writes."""
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if request.headers.get("X-Requested-With") != "VoteStupid" or (origin and origin not in allowed_origins()):
            raise HTTPException(403, "La petición administrativa no está autorizada.")


def session_db():
    """Provide an independent SQL session for authenticating and revoking sessions."""
    from app.infrastructure.database.session import SessionLocal
    with SessionLocal() as db:
        yield db


def require_admin_session(request: Request, db: Session = Depends(session_db)) -> AdminSessionModel:
    """Authorize only unexpired cookies associated with the current password."""
    protect_admin_request(request)
    token = request.cookies.get(COOKIE_NAME, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(401, "Inicia sesión para acceder a la administración.")
    session = db.get(AdminSessionModel, session_hash(token))
    if not session or session.expires_at <= datetime.now(timezone.utc) or session.credential_version != credential_version():
        raise HTTPException(401, "La sesión ha caducado. Vuelve a iniciar sesión.")
    return session


def create_session(request: Request, db: Session) -> tuple[str, datetime]:
    """Rotate the session, prune expired entries, and bound the number of stored sessions."""
    now = datetime.now(timezone.utc)
    old = request.cookies.get(COOKIE_NAME, "")
    db.execute(delete(AdminSessionModel).where(AdminSessionModel.expires_at <= now))
    if old:
        db.execute(delete(AdminSessionModel).where(AdminSessionModel.token_hash == session_hash(old)))
    sessions = db.scalars(select(AdminSessionModel).order_by(AdminSessionModel.expires_at.desc()).offset(99)).all()
    for session in sessions:
        db.delete(session)
    token = secrets.token_urlsafe(32)
    expires = now + timedelta(hours=8)
    db.add(AdminSessionModel(token_hash=session_hash(token), credential_version=credential_version(), expires_at=expires))
    db.commit()
    return token, expires
