import random
import string
from sqlalchemy.orm import Session
from app.models.account import Account


def generate_account_number(db: Session) -> str:
    while True:
        # Generate a 10-digit account number starting with 4 (like US banks)
        number = "4" + "".join([str(random.randint(0, 9)) for _ in range(9)])
        # Make sure it doesn't already exist
        exists = db.query(Account).filter(Account.account_number == number).first()
        if not exists:
            return number


def generate_transaction_reference() -> str:
    prefix = "ARC"
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=12))
    return f"{prefix}-{random_part}"