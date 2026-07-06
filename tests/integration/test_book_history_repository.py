from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BibliographicRecord, BookEventType, BookHistory, OwnedBook
from app.infrastructure.repositories import (
	SQLAlchemyBibliographicRecordRepository,
	SQLAlchemyBookHistoryRepository,
	SQLAlchemyOwnedBookRepository,
)


async def test_save_then_find_by_book_returns_real_enum_members_not_raw_strings(
	db_session: AsyncSession, library_id: UUID
) -> None:
	record = await SQLAlchemyBibliographicRecordRepository(db_session).save(
		BibliographicRecord(library_id=library_id, title="Test Book")
	)
	book = await SQLAlchemyOwnedBookRepository(db_session).save(
		OwnedBook(library_id=library_id, bibliographic_record_id=record.id)
	)
	history_repo = SQLAlchemyBookHistoryRepository(db_session)

	await history_repo.save(
		BookHistory(owned_book_id=book.id, event_type=BookEventType.CREATED, changed_by=uuid4())
	)

	entries = await history_repo.find_by_book(book.id)
	assert len(entries) == 1
	# Identity check: a raw string equal to "created" would also satisfy
	# `== BookEventType.CREATED` (StrEnum), so only `is` proves the repository
	# returns a real enum member rather than the unconverted DB column value.
	assert entries[0].event_type is BookEventType.CREATED
