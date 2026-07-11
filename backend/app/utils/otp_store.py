import random
from datetime import datetime, timedelta
from typing import Dict, Optional

# In-memory store: {email: {"otp": str, "expires_at": datetime}}
_otp_store: Dict[str, dict] = {}

def generate_otp(email: str) -> str:
    """Generate a 6-digit OTP code and store it with a 60-minute expiration time."""
    otp = f"{random.randint(100000, 999999)}"
    expires_at = datetime.utcnow() + timedelta(minutes=60)
    _otp_store[email.lower()] = {
        "otp": otp,
        "expires_at": expires_at
    }
    return otp

def verify_otp(email: str, code: str) -> bool:
    """Verify the 6-digit OTP code. Returns True if valid and not expired, false otherwise.
    The OTP is cleared after successful verification to prevent reuse.
    """
    email_key = email.lower()
    if email_key not in _otp_store:
        return False
        
    entry = _otp_store[email_key]
    if datetime.utcnow() > entry["expires_at"]:
        # Expired, clean up
        del _otp_store[email_key]
        return False
        
    if entry["otp"] == code:
        # Valid, clean up and return True
        del _otp_store[email_key]
        return True
        
    return False
