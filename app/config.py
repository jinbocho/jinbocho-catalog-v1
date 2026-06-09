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
    allowed_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
