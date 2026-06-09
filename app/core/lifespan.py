from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
	http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
	app.state.http_client = http_client
	yield
	await http_client.aclose()
