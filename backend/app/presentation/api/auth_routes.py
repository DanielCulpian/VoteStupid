from fastapi import APIRouter, Depends, Request, Response, HTTPException
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.orm import Session

from app.infrastructure.security.admin_session import (
    COOKIE_NAME, create_session, protect_admin_request, require_admin_session,
    secure_cookie, session_db, session_hash, verify_password,
)
from app.infrastructure.models.admin_session_model import AdminSessionModel

router = APIRouter(prefix="/api/admin/auth")


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: SecretStr = Field(min_length=1, max_length=256)


@router.post("/login", dependencies=[Depends(protect_admin_request)])
def login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(session_db)):
    """Verify the password and deliver the secret exclusively through an HttpOnly cookie."""
    wait = request.app.state.rate_limiter.check("admin-login-global", "login_total")
    if wait:
        raise HTTPException(429, "Demasiados intentos. Inténtalo más tarde.", headers={"Retry-After": str(wait)})
    if not verify_password(data.password.get_secret_value()):
        raise HTTPException(401, "La contraseña no es correcta.")
    token, expires = create_session(request, db)
    response.set_cookie(COOKIE_NAME, token, max_age=28800, expires=expires, httponly=True,
                        secure=secure_cookie(), samesite="strict", path="/api")
    return {"authenticated": True, "expires_at": expires}


@router.get("/session")
def current_session(session: AdminSessionModel = Depends(require_admin_session)):
    """Check the session without returning its secret or hashes."""
    return {"authenticated": True, "expires_at": session.expires_at}


@router.delete("/session", dependencies=[Depends(protect_admin_request)])
def logout(request: Request, response: Response, db: Session = Depends(session_db)):
    """Revoke the server-side cookie session even if the browser retains a copy."""
    session = db.get(AdminSessionModel, session_hash(request.cookies.get(COOKIE_NAME, "")))
    if session:
        db.delete(session)
        db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api", secure=secure_cookie(), httponly=True, samesite="strict")
    return {"authenticated": False}
