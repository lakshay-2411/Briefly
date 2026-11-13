from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    tavily_api_key: str = ""

    gnani_api_key: str = ""
    gnani_voice_id: str = ""

    brevo_api_key: str = ""
    email_from: str = ""

    frontend_url: str = "http://localhost:3000"
    generation_lead_minutes: int = 10


settings = Settings()
