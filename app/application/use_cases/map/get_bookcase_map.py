from dataclasses import dataclass
from uuid import UUID

from app.application.use_cases.export import ExportBookItem
from app.domain.entities import Bookcase, Section, Shelf
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookReadRepository,
	OwnedBookRepository,
	SectionRepository,
	ShelfRepository,
)


@dataclass
class MapShelfBooks:
	shelf: Shelf
	books: list[ExportBookItem]


@dataclass
class MapSectionData:
	section: Section
	shelves: list[MapShelfBooks]


class GetBookcaseMapUseCase:
	def __init__(
		self,
		bookcase_repo: BookcaseRepository,
		section_repo: SectionRepository,
		shelf_repo: ShelfRepository,
		book_repo: OwnedBookRepository,
		record_repo: BibliographicRecordRepository,
		read_repo: BookReadRepository,
	) -> None:
		self._bookcase_repo = bookcase_repo
		self._section_repo = section_repo
		self._shelf_repo = shelf_repo
		self._book_repo = book_repo
		self._record_repo = record_repo
		self._read_repo = read_repo

	async def execute(
		self, family_id: UUID, bookcase_id: UUID, viewer_id: UUID
	) -> tuple[Bookcase, list[MapSectionData]]:
		bookcase = await self._bookcase_repo.find_by_id(bookcase_id)
		if bookcase is None:
			raise LookupError("Bookcase not found")
		if bookcase.family_id != family_id:
			raise PermissionError("Access denied")

		sections = await self._section_repo.find_all_by_bookcase(bookcase_id, limit=200, offset=0)
		shelves_by_section: dict[UUID, list[Shelf]] = {}
		shelf_ids: list[UUID] = []
		for section in sections:
			section_shelves = await self._shelf_repo.find_all_by_section(section.id, limit=500, offset=0)
			shelves_by_section[section.id] = section_shelves
			shelf_ids.extend(shelf.id for shelf in section_shelves)

		books = await self._book_repo.find_all_by_shelf_ids(shelf_ids)
		read_ids = await self._read_repo.list_read_book_ids([book.id for book in books], viewer_id)
		for book in books:
			book.reading_status = book.reading_status_for(viewer_id, book.id in read_ids)
		records = await self._record_repo.find_all_by_ids([book.bibliographic_record_id for book in books])
		record_map = {record.id: record for record in records}
		books_by_shelf: dict[UUID, list[ExportBookItem]] = {}
		for book in books:
			if book.shelf_id is None:
				continue
			books_by_shelf.setdefault(book.shelf_id, []).append(
				ExportBookItem(book=book, record=record_map.get(book.bibliographic_record_id))
			)

		mapped_sections: list[MapSectionData] = []
		for section in sections:
			mapped_sections.append(
				MapSectionData(
					section=section,
					shelves=[
						MapShelfBooks(shelf=shelf, books=books_by_shelf.get(shelf.id, []))
						for shelf in shelves_by_section.get(section.id, [])
					],
				)
			)
		return bookcase, mapped_sections
