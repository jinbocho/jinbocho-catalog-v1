from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool = False
    database_url: str
    open_library_url: str = "https://openlibrary.org"
    google_books_url: str = "https://www.googleapis.com/books/v1"
    google_books_api_key: str = ""  # optional — without key, quota is shared/limited
    isbn_cache_ttl_days: int = 30
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "jinbocho-auth"
    jwt_audience: str = "jinbocho"
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    auth_service_url: str = "http://localhost:8001"
    internal_service_token: str = ""
    loan_reminder_lead_days: int = 1
    ai_service_url: str = "http://jinbocho-ai:8003"
    ai_internal_service_token: str = ""
    fuzzy_dedup_high_threshold: float = 0.92
    fuzzy_dedup_low_threshold: float = 0.60

    # Comma-separated list of modules enabled for this installation — must match
    # api-gateway's JINBOCHO_FEATURES. The gateway enforces this for public AI
    # routes; catalog-service checks it itself before its own server-to-server
    # call to ai-service's /dedup, since that call never passes through the gateway.
    jinbocho_features: str = "catalog,auth"

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def ai_module_enabled(self) -> bool:
        return "ai" in [f.strip() for f in self.jinbocho_features.split(",")]


settings = Settings()  # type: ignore[call-arg]
