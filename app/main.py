from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import app.infrastructure.models  # noqa: F401 - Register ORM models

from app.api.v1.router import router as v1_router
from app.config import settings
from app.core import OPENAPI_CONFIG, SECURITY_SCHEME, configure_exception_handlers, lifespan
from app.infrastructure.database.session import get_db
from app.limiter import limiter


def create_app() -> FastAPI:
	app = FastAPI(
		title=OPENAPI_CONFIG["title"],
		description=OPENAPI_CONFIG["description"],
		version=OPENAPI_CONFIG["version"],
		debug=settings.debug,
		lifespan=lifespan,
	)

	# Register exception handlers
	configure_exception_handlers(app)

	# Setup rate limiting
	app.state.limiter = limiter
	app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
	app.add_middleware(SlowAPIMiddleware)

	# Setup CORS
	app.add_middleware(
		CORSMiddleware,
		allow_origins=settings.allowed_origins,
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	# Include API router with /v1 prefix
	app.include_router(v1_router, prefix="/v1")

	# Health check endpoint
	@app.get("/health", tags=["health"])
	async def health(db: AsyncSession = Depends(get_db)):
		try:
			await db.execute(text("SELECT 1"))
			return {"status": "ok", "service": "catalog-service", "db": "ok"}
		except Exception:
			return JSONResponse(status_code=503, content={"status": "error", "db": "unreachable"})

	# Add OpenAPI security scheme
	original_openapi = app.openapi

	def custom_openapi():
		if app.openapi_schema:
			return app.openapi_schema
		openapi_schema = original_openapi()
		openapi_schema["components"]["securitySchemes"] = SECURITY_SCHEME
		openapi_schema["tags"] = OPENAPI_CONFIG.get("tags", [])
		app.openapi_schema = openapi_schema
		return openapi_schema

	app.openapi = custom_openapi

	return app


app = create_app()
