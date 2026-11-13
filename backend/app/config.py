from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_fallback_model: str = "gemini-3.5-flash"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    tavily_api_key: str = ""

    gnani_api_key: str = ""
    gnani_model: str = "timbre-v2.5"
    gnani_voice_id: str = "Kaveri"
    gnani_language: str = "en-IN"
    gnani_max_chars: int = 500

    brevo_api_key: str = ""
    email_from: str = ""
    email_from_name: str = "Daily Briefing"

    frontend_url: str = "http://localhost:3000"
    generation_lead_minutes: int = 10


settings = Settings()
