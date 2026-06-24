from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import (
	get_bibliographic_record_repository,
	get_book_read_repository,
	get_bookcase_repository,
	get_current_user_payload,
	get_owned_book_repository,
	get_section_repository,
	get_shelf_repository,
)
from app.api.v1.schemas.map_schemas import (
	BookcaseMapResponse,
	BookOnShelfResponse,
	SectionMapResponse,
	ShelfMapResponse,
)
from app.application.use_cases import GetBookcaseMapUseCase
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookReadRepository,
	OwnedBookRepository,
	SectionRepository,
	ShelfRepository,
)

router = APIRouter(tags=["map"])


@router.get("/bookcase/{bookcase_id}", response_model=BookcaseMapResponse, summary="Get bookcase map")
async def get_bookcase_map(
	bookcase_id: UUID,
	payload: dict[str, Any] = Depends(get_current_user_payload),
	bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
	section_repo: SectionRepository = Depends(get_section_repository),
	shelf_repo: ShelfRepository = Depends(get_shelf_repository),
	book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
	record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
	read_repo: BookReadRepository = Depends(get_book_read_repository),
) -> BookcaseMapResponse:
	use_case = GetBookcaseMapUseCase(bookcase_repo, section_repo, shelf_repo, book_repo, record_repo, read_repo)
	bookcase, sections_data = await use_case.execute(
		UUID(payload["family_id"]), bookcase_id, viewer_id=UUID(payload["sub"])
	)

	# Transform to response format
	sections = [
		SectionMapResponse(
			section_id=section.section.id,
			section_index=section.section.section_index,
			label=section.section.label,
			shelves=[
				ShelfMapResponse(
					shelf_id=shelf_books.shelf.id,
					shelf_index=shelf_books.shelf.shelf_index,
					books=[
						BookOnShelfResponse(
							id=item.book.id,
							title=item.record.title if item.record else None,
							main_author=item.record.main_author if item.record else None,
							reading_status=item.book.reading_status,
						)
						for item in shelf_books.books
					]
				)
				for shelf_books in section.shelves
			]
		)
		for section in sections_data
	]

	return BookcaseMapResponse(
		bookcase_id=bookcase.id,
		bookcase_name=bookcase.name,
		sections=sections
	)
