from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


def configure_exception_handlers(app: FastAPI) -> None:
	@app.exception_handler(LookupError)
	async def lookup_error_handler(request, exc):
		return JSONResponse(
			status_code=status.HTTP_404_NOT_FOUND,
			content={"detail": str(exc)},
		)

	@app.exception_handler(PermissionError)
	async def permission_error_handler(request, exc):
		return JSONResponse(
			status_code=status.HTTP_403_FORBIDDEN,
			content={"detail": str(exc)},
		)

	@app.exception_handler(ValueError)
	async def value_error_handler(request, exc):
		return JSONResponse(
			status_code=status.HTTP_409_CONFLICT,
			content={"detail": str(exc)},
		)

	@app.exception_handler(IntegrityError)
	async def integrity_error_handler(request, exc):
		return JSONResponse(
			status_code=status.HTTP_409_CONFLICT,
			content={"detail": "Data integrity violation"},
		)
