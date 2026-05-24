import os
import sys
from decimal import Decimal

# Add backend directory to path to import app items
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from app.database import SessionLocal, Base, engine
    from app.models.user import User, IDType, CitizenshipStatus, EmploymentStatus, AccountPurpose
    from app.models.account import Account
    from app.utils.hashing import hash_pin, hash_password
except ImportError as e:
    print(f"Error importing app modules: {e}")
    sys.exit(1)

def seed():
    # 1. Initialize Tables
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 2. Check for users, create if missing
        users = db.query(User).all()
        if not users:
            print("No users found. Creating two test users...")
            user1 = User(
                first_name="Des", last_name="Ny", email="desnyguy@gmail.com",
                hashed_password=hash_password("password123"),
                is_kyc_complete=True, is_id_verified=True
            )
            user2 = User(
                first_name="Anita", last_name="Bechemi", email="anitabechemi@gmail.com",
                hashed_password=hash_password("password123"),
                is_kyc_complete=True, is_id_verified=True
            )
            db.add(user1)
            db.add(user2)
            db.flush()
            
            # Create accounts for them
            acc1 = Account(user_id=user1.id, account_number="1234567890", balance=Decimal("50000.00"))
            acc2 = Account(user_id=user2.id, account_number="0987654321", balance=Decimal("50000.00"))
            db.add(acc1)
            db.add(acc2)
            print(f"Created user john@example.com (Acc: 1234567890) and jane@example.com (Acc: 0987654321)")
            users = [user1, user2]

        print(f"Found {len(users)} users. Preparing to set PINs and balance...")
        
        test_pin_hash = hash_pin("1234")

        for user in users:
            user.transaction_pin = test_pin_hash
            account = db.query(Account).filter(Account.user_id == user.id).first()
            if account:
                account.balance = Decimal("50000.00")
                print(f"Updated Acc {account.account_number} ({user.email}) -> $50k, PIN: 1234")

        db.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
