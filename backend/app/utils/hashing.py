import bcrypt

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def hash_pin(pin: str) -> str:
    pin_bytes = pin.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pin_bytes, salt).decode('utf-8')

def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    return bcrypt.checkpw(
        plain_pin.encode('utf-8'),
        hashed_pin.encode('utf-8')
    )