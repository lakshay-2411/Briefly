from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    groq_api_key: str = ""
    groq_models: str = "openai/gpt-oss-120b,qwen/qwen3.8-27b,openai/gpt-oss-20b"  # tried in order
    openrouter_api_key: str = ""
    openrouter_models: str = "nvidia/nemotron-3.5-super-vl:free,nvidia/nemotron-3-ultra-550b-a55b:free,google/gemma-4-31b-it:free"  # free models, tried after Groq
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
