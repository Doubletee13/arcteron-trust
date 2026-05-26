import os
import sys
from decimal import Decimal

# Add backend directory to path to import app items
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from app.database import SessionLocal, Base, engine
    from app.models.user import User, IDType, CitizenshipStatus, EmploymentStatus, AccountPurpose, UserRole, UserStatus
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
        # 2. Create Admin 1 (Primary)
        admin1 = db.query(User).filter(User.email == "admin@arcterontrust.com").first()
        if not admin1:
            print("Creating first admin user...")
            admin1 = User(
                first_name="System",
                last_name="Administrator",
                email="admin@arcterontrust.com",
                hashed_password=hash_password("Admin@1234"),
                role=UserRole.admin,
                status=UserStatus.active,
                is_email_verified=True,
                is_kyc_complete=True,
                is_id_verified=True
            )
            db.add(admin1)
            db.flush()
            
            admin_account = Account(user_id=admin1.id, account_number="0000000001", balance=Decimal("0.00"))
            db.add(admin_account)
            print("Created admin user: admin@arcterontrust.com (Acc: 0000000001) - Password: Admin@1234")
            
        # 3. Create Admin 2 (Support)
        admin2 = db.query(User).filter(User.email == "support@arcterontrust.com").first()
        if not admin2:
            print("Creating second admin user...")
            admin2 = User(
                first_name="Support",
                last_name="Administrator",
                email="support@arcterontrust.com",
                hashed_password=hash_password("Support@1234"),
                role=UserRole.admin,
                status=UserStatus.active,
                is_email_verified=True,
                is_kyc_complete=True,
                is_id_verified=True
            )
            db.add(admin2)
            db.flush()
            
            support_account = Account(user_id=admin2.id, account_number="0000000002", balance=Decimal("0.00"))
            db.add(support_account)
            print("Created support admin: support@arcterontrust.com (Acc: 0000000002) - Password: Support@1234")

        db.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
