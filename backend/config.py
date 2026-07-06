from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_role_key: str

    # Gemini
    gemini_api_key: str

    # Meta WhatsApp Cloud API
    whatsapp_access_token: str
    whatsapp_phone_number_id: str
    whatsapp_business_account_id: str
    whatsapp_verify_token: str
    meta_app_id: str = ""         # ← single declaration
    meta_app_secret: str = ""     # ← single declaration

    # App
    secret_key: str = "change-this-in-production"
    frontend_url: str = "https://691a-102-91-104-187.ngrok-free.app"

    # Paystack
    paystack_secret_key: str = ""
    paystack_webhook_secret: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    return Settings()
