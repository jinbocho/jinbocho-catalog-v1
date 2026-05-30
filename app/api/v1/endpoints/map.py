from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.dependencies import (
    get_bibliographic_record_repository,
    get_bookcase_repository,
    get_current_user_payload,
    get_owned_book_repository,
    get_section_repository,
    get_shelf_repository,
)
from app.application.use_cases import GetBookcaseMapUseCase
from app.domain.repositories import BibliographicRecordRepository, BookcaseRepository, OwnedBookRepository, SectionRepository, ShelfRepository

router = APIRouter()


class BookOnShelfResponse(BaseModel):
    id: UUID
    title: str | None = None
    main_author: str | None = None
    cover_url: str | None = None
    shelf_position: int | None = None
    reading_status: str


class ShelfMapResponse(BaseModel):
    id: UUID
    shelf_index: int
    notes: str | None = None
    books: list[BookOnShelfResponse]


class SectionMapResponse(BaseModel):
    id: UUID
    section_index: int
    label: str | None = None
    shelves: list[ShelfMapResponse]


class BookcaseMapResponse(BaseModel):
    id: UUID
    name: str
    room_id: UUID
    sections: list[SectionMapResponse]


@router.get("/bookcases/{bookcase_id}", response_model=BookcaseMapResponse)
async def get_bookcase_map(
    bookcase_id: UUID,
    payload: dict = Depends(get_current_user_payload),
    bookcase_repo: BookcaseRepository = Depends(get_bookcase_repository),
    section_repo: SectionRepository = Depends(get_section_repository),
    shelf_repo: ShelfRepository = Depends(get_shelf_repository),
    book_repo: OwnedBookRepository = Depends(get_owned_book_repository),
    record_repo: BibliographicRecordRepository = Depends(get_bibliographic_record_repository),
):
    try:
        bookcase, sections = await GetBookcaseMapUseCase(
            bookcase_repo=bookcase_repo,
            section_repo=section_repo,
            shelf_repo=shelf_repo,
            book_repo=book_repo,
            record_repo=record_repo,
        ).execute(UUID(payload["family_id"]), bookcase_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Bookcase not found")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    return BookcaseMapResponse(
        id=bookcase.id,
        name=bookcase.name,
        room_id=bookcase.room_id,
        sections=[
            SectionMapResponse(
                id=section_data.section.id,
                section_index=section_data.section.section_index,
                label=section_data.section.label,
                shelves=[
                    ShelfMapResponse(
                        id=shelf_data.shelf.id,
                        shelf_index=shelf_data.shelf.shelf_index,
                        notes=shelf_data.shelf.notes,
                        books=[
                            BookOnShelfResponse(
                                id=item.book.id,
                                title=item.record.title if item.record else None,
                                main_author=item.record.main_author if item.record else None,
                                cover_url=item.record.cover_url if item.record else None,
                                shelf_position=item.book.shelf_position,
                                reading_status=item.book.reading_status,
                            )
                            for item in shelf_data.books
                        ],
                    )
                    for shelf_data in section_data.shelves
                ],
            )
            for section_data in sections
        ],
    )
