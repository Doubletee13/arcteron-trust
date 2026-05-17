from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import Base, engine
import app.models
from app.routers import auth

app = FastAPI(
    title=settings.APP_NAME,
    description="Arcteron Trust Banking API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# Register routers
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Arcteron Trust API is running"}