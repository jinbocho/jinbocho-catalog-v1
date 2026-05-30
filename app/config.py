from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    debug: bool = False
    database_url: str
    auth_service_url: str = "http://auth-service:8001"
    open_library_url: str = "https://openlibrary.org"
    google_books_url: str = "https://www.googleapis.com/books/v1"
    isbn_cache_ttl_days: int = 30

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
