from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user_payload, get_http_client
from app.infrastructure.database.session import engine, get_db
from app.main import app


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
	"""A session bound to a connection-level transaction that is always rolled
	back at the end of the test, so integration tests can exercise the real
	ORM/Postgres round-trip without leaving any data behind."""
	async with engine.connect() as connection:
		await connection.begin()
		session = AsyncSession(bind=connection, expire_on_commit=False)
		try:
			yield session
		finally:
			await session.close()
			await connection.rollback()


@pytest.fixture
def library_id() -> UUID:
	return uuid4()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, library_id: UUID) -> AsyncGenerator[AsyncClient, None]:
	"""An HTTP client wired to the real app, with get_db overridden to reuse
	the same rolled-back-on-exit session as db_session (so a test can assert
	through the API and still inspect rows via a repository in the same
	uncommitted transaction), and JWT auth overridden to a fixed admin payload
	for `library_id` — issuing/validating real tokens is auth-service's concern,
	not catalog-service's; this exercises the full endpoint -> use case ->
	repository -> Postgres flow without re-testing auth-service's job. The
	app's real http_client is only set up by the lifespan context (not run
	under ASGITransport), so get_http_client is overridden too; nothing in
	these tests exercises the external ISBN-lookup HTTP calls anyway."""

	async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
		yield db_session

	async def _override_get_current_user_payload() -> dict[str, Any]:
		return {"library_id": str(library_id), "sub": str(uuid4()), "role": "admin"}

	async def _override_get_http_client() -> AsyncGenerator[AsyncClient, None]:
		async with AsyncClient() as http_client:
			yield http_client

	app.dependency_overrides[get_db] = _override_get_db
	app.dependency_overrides[get_current_user_payload] = _override_get_current_user_payload
	app.dependency_overrides[get_http_client] = _override_get_http_client
	try:
		transport = ASGITransport(app=app)
		async with AsyncClient(transport=transport, base_url="http://test") as ac:
			yield ac
	finally:
		app.dependency_overrides.pop(get_db, None)
		app.dependency_overrides.pop(get_current_user_payload, None)
		app.dependency_overrides.pop(get_http_client, None)
