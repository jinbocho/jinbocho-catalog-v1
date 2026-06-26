from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.domain.errors import DuplicateBookError


def configure_exception_handlers(app: FastAPI) -> None:
	@app.exception_handler(LookupError)
	async def lookup_error_handler(request: Request, exc: LookupError) -> JSONResponse:
		return JSONResponse(
			status_code=status.HTTP_404_NOT_FOUND,
			content={"detail": str(exc)},
		)

	@app.exception_handler(PermissionError)
	async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
		return JSONResponse(
			status_code=status.HTTP_403_FORBIDDEN,
			content={"detail": str(exc)},
		)

	@app.exception_handler(ValueError)
	async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
		return JSONResponse(
			status_code=status.HTTP_409_CONFLICT,
			content={"detail": str(exc)},
		)

	@app.exception_handler(IntegrityError)
	async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
		return JSONResponse(
			status_code=status.HTTP_409_CONFLICT,
			content={"detail": "Data integrity violation"},
		)

	@app.exception_handler(DuplicateBookError)
	async def duplicate_book_error_handler(request: Request, exc: DuplicateBookError) -> JSONResponse:
		conflict = exc.conflict
		return JSONResponse(
			status_code=status.HTTP_409_CONFLICT,
			content={
				"error": "duplicate_book",
				"conflict_type": conflict.conflict_type,
				"existing_book_id": str(conflict.existing_book_id),
				"existing_record_id": str(conflict.existing_record_id),
				"title": conflict.title,
				"main_author": conflict.main_author,
				"isbn": conflict.isbn,
				"existing_owner_id": str(conflict.existing_owner_id) if conflict.existing_owner_id else None,
				"existing_room_id": str(conflict.existing_room_id) if conflict.existing_room_id else None,
				"existing_bookcase_id": str(conflict.existing_bookcase_id) if conflict.existing_bookcase_id else None,
				"existing_section_id": str(conflict.existing_section_id) if conflict.existing_section_id else None,
				"existing_shelf_id": str(conflict.existing_shelf_id) if conflict.existing_shelf_id else None,
				"match_reason": conflict.match_reason,
			},
		)
