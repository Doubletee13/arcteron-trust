from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.jwt import decode_access_token
from app.models.user import User, UserRole, UserStatus

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    if isinstance(payload, dict) and payload.get("error") == "expired":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Allow blocked users to access their profile, but they'll be blocked from transactions
    # Transaction endpoints should check user.status separately
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active"
        )
    return current_user


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role not in [UserRole.admin, UserRole.superadmin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    if current_user.status == UserStatus.blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your admin account has been blocked"
        )
    return current_user


def require_superadmin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.role != UserRole.superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required"
        )
    return current_user