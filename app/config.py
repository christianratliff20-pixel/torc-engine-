from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/clipping_engine"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:5173"
    anthropic_api_key: str = ""
    secret_key: str = "dev-only-insecure-secret-change-me"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter_weekly: str = ""
    stripe_price_starter_monthly: str = ""
    stripe_price_starter_annual: str = ""
    stripe_price_pro_weekly: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_pro_annual: str = ""
    stripe_price_studio_monthly: str = ""
    stripe_price_studio_annual: str = ""
    frontend_url: str = "http://localhost:5173"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@example.com"

    class Config:
        env_file = ".env"


settings = Settings()
