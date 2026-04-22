from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # Gemini
    gemini_api_key: str

    # Meta WhatsApp Cloud API
    whatsapp_access_token: str        # Meta App → WhatsApp → API Setup
    whatsapp_phone_number_id: str     # Meta App → WhatsApp → API Setup
    whatsapp_business_account_id: str # Meta App → WhatsApp → API Setup
    whatsapp_verify_token: str        # you make this up — for webhook verification

    # App
    secret_key: str = "dev-secret-change-in-prod"
    frontend_url: str = "http://localhost:3000"

    # Paystack (leave blank until ready to go live)
    paystack_secret_key: str = ""
    paystack_webhook_secret: str = ""

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()