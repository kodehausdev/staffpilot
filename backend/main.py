from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.webhook import router as webhook_router
from routers.admin import router as admin_router
from routers.billing import router as billing_router
from routers.settings import router as settings_router
from config import get_settings

app = FastAPI(
    title="StaffPilot API",
    description="AI-powered WhatsApp HR bot for Nigerian companies",
    version="0.1.0",
)

_settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.frontend_url],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router)
app.include_router(admin_router)
app.include_router(billing_router)
app.include_router(settings_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "staffpilot"}


@app.get("/")
def root():
    return {"message": "StaffPilot API is running"}


