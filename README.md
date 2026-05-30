# catalog-service

`catalog-service` is the main transactional service for Jinbocho.
It combines location management, bibliographic records, owned books, ingestion, audit, and export in a single FastAPI service.

## Responsibilities

- Manage rooms, bookcases, sections, and shelves.
- Manage bibliographic records and owned books.
- Keep book creation plus positioning inside one transaction.
- Provide search, history, export, and ISBN metadata lookup.

## Internal modules

- `location`: rooms, bookcases, sections, shelves
- `catalog`: bibliographic records and owned books
- `ingestion`: ISBN lookup and cache

## Environment variables

| Variable | Description |
|---|---|
| `DEBUG` | Enables debug SQL logging |
| `DATABASE_URL` | Async SQLAlchemy connection string |
| `AUTH_SERVICE_URL` | Internal auth service URL |
| `OPEN_LIBRARY_URL` | Open Library base URL |
| `GOOGLE_BOOKS_URL` | Google Books base URL |
| `ISBN_CACHE_TTL_DAYS` | TTL for cached ISBN metadata |

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

## Run with Docker

```bash
docker build -t jinbocho-catalog-service .
docker run --rm -p 8002:8002 --env-file .env jinbocho-catalog-service
```

## Health check

- `GET /health`

## Notes

- The service creates its tables on startup for scaffolding convenience.
- ISBN lookup checks the local cache first, then Open Library, then Google Books.
