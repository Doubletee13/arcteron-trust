import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CardBase(BaseModel):
    pass

class CardCreate(CardBase):
    pass

class CardResponse(CardBase):
    id: uuid.UUID
    card_number: str
    card_holder_name: str
    expiry_date: str
    cvv: str
    is_active: bool
    is_physical: bool
    card_type: str
    network: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
