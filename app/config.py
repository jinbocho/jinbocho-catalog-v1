from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool = False
    database_url: str
    open_library_url: str = "https://openlibrary.org"
    open_library_covers_url: str = "https://covers.openlibrary.org"
    open_library_cover_size: str = "M"  # S, M, L
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
    # GDPR Art. 5(1)(e) storage limitation — unified retention window for
    # removed_members snapshots and returned-loan borrower names (see
    # PurgeExpiredPersonalDataUseCase). Declared to users in the Privacy Policy;
    # keep the two in sync if this changes.
    retention_months: int = 12
    ai_service_url: str = "http://jinbocho-ai:8003"
    ai_internal_service_token: str = ""
    fuzzy_dedup_high_threshold: float = 0.92
    fuzzy_dedup_low_threshold: float = 0.60

    # Comma-separated list of modules enabled for this installation — must match
    # api-gateway's JINBOCHO_FEATURES. Available values: catalog, auth, ai, kids.
    # The gateway enforces "ai" for public AI routes; catalog-service checks it
    # itself before its own server-to-server calls to ai-service (/dedup, quiz
    # generation, discussion generation), since those never pass through the
    # gateway. "kids_mode_enabled" on each use case comes from the Library
    # record/JWT claim, not from this flag — "kids" isn't consulted here at all.
    jinbocho_features: str = "catalog,auth"

    # Observability (ADR-012) — off by default so a service run without the
    # optional Alloy collector container behaves exactly as before.
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://alloy:4318"

    # Error tracking (ADR-012 Phase 1) — off by default. Point at a GlitchTip
    # instance or Sentry Cloud (EU region); only unhandled 5xx bugs are ever
    # reported (see configure_error_tracking).
    sentry_dsn: str | None = None
    sentry_environment: str = "production"

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def ai_module_enabled(self) -> bool:
        return "ai" in [f.strip() for f in self.jinbocho_features.split(",")]


settings = Settings()  # type: ignore[call-arg]
