from typing import Optional
from itsdangerous import URLSafeTimedSerializer
from app.config import settings

serializer = URLSafeTimedSerializer(settings.SECRET_KEY)


def generate_reset_token(email: str) -> str:
    return serializer.dumps(email, salt="reset-password")


def verify_reset_token(token: str, max_age: int = 3600) -> Optional[str]:
    try:
        email = serializer.loads(token, salt="reset-password", max_age=max_age)
        return email
    except Exception:
        return None


def generate_pin_reset_token(email: str) -> str:
    return serializer.dumps(email, salt="reset-pin")


def verify_pin_reset_token(token: str, max_age: int = 3600) -> Optional[str]:
    try:
        email = serializer.loads(token, salt="reset-pin", max_age=max_age)
        return email
    except Exception:
        return None