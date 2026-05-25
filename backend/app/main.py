from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import Base, engine
import app.models
from app.routers import auth
from app.routers import transactions
from app.routers import notifications
from app.routers import transfers
from app.routers import admin
from app.routers import cards

app = FastAPI(
    title=settings.APP_NAME,
    description="Arcteron Trust Banking API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "https://arcteron-trust.vercel.app",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(notifications.router)
app.include_router(transfers.router)
app.include_router(admin.router)
app.include_router(cards.router, prefix="/api/cards", tags=["cards"])

@app.get("/")
def root():
    return {"message": "Arcteron Trust API is running"}