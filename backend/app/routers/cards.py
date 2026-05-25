import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import database
from app.models.card import Card
from app.models.account import Account
from app.models.user import User
from app.schemas.card import CardResponse
from app.routers.auth import get_current_user

router = APIRouter()

def generate_card_number():
    prefix = random.choice(["51", "52", "53", "54", "55"]) # Mastercard
    rest = ''.join([str(random.randint(0, 9)) for _ in range(14)])
    num = prefix + rest
    return f"{num[:4]} {num[4:8]} {num[8:12]} {num[12:]}"

@router.get("/me", response_model=CardResponse)
def get_my_card(current_user: User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    card = db.query(Card).filter(Card.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="No card found")
    return card

@router.post("/request", response_model=CardResponse)
def request_card(current_user: User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    existing = db.query(Card).filter(Card.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already has a card")
    
    account = db.query(Account).filter(Account.user_id == current_user.id).first()
    if not account:
        raise HTTPException(status_code=400, detail="User must have an account to request a card")
    
    expiry_dt = datetime.utcnow() + timedelta(days=365*4)
    expiry_str = f"{expiry_dt.month:02d}/{str(expiry_dt.year)[-2:]}"
    cvv = f"{random.randint(100, 999):03d}"
    
    new_card = Card(
        user_id=current_user.id,
        account_id=account.id,
        card_number=generate_card_number(),
        card_holder_name=f"{current_user.first_name} {current_user.last_name}".upper(),
        expiry_date=expiry_str,
        cvv=cvv,
        is_active=True,
        network="mastercard"
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card

@router.post("/{card_id}/toggle-freeze")
def toggle_freeze(card_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(database.get_db)):
    card = db.query(Card).filter(Card.id == card_id, Card.user_id == current_user.id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    card.is_active = not card.is_active
    db.commit()
    return {"message": "Card status updated", "is_active": card.is_active}
