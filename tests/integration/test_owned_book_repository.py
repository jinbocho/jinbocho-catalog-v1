from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BibliographicRecord, BookCondition, BookSource, OwnedBook, ReadingStatus
from app.infrastructure.repositories import SQLAlchemyBibliographicRecordRepository, SQLAlchemyOwnedBookRepository


async def _make_record(db_session: AsyncSession, library_id: UUID) -> BibliographicRecord:
	record_repo = SQLAlchemyBibliographicRecordRepository(db_session)
	return await record_repo.save(BibliographicRecord(library_id=library_id, title="Test Book"))


async def test_save_then_find_by_id_returns_real_enum_members_not_raw_strings(
	db_session: AsyncSession, library_id: UUID
) -> None:
	record = await _make_record(db_session, library_id)
	book_repo = SQLAlchemyOwnedBookRepository(db_session)

	saved = await book_repo.save(
		OwnedBook(
			library_id=library_id,
			bibliographic_record_id=record.id,
			condition=BookCondition.GOOD,
			source=BookSource.GIFT,
			reading_status=ReadingStatus.READING,
		)
	)

	found = await book_repo.find_by_id(saved.id)
	assert found is not None

	# Identity check, not equality: a plain str equal to "reading" would also
	# pass `== ReadingStatus.READING` (StrEnum), so only `is` actually proves
	# the ORM boundary returns real enum members instead of raw column strings.
	assert found.reading_status is ReadingStatus.READING
	assert found.condition is BookCondition.GOOD
	assert found.source is BookSource.GIFT


async def test_save_then_find_by_id_round_trips_nullable_enum_fields_as_none(
	db_session: AsyncSession, library_id: UUID
) -> None:
	record = await _make_record(db_session, library_id)
	book_repo = SQLAlchemyOwnedBookRepository(db_session)

	saved = await book_repo.save(OwnedBook(library_id=library_id, bibliographic_record_id=record.id))

	found = await book_repo.find_by_id(saved.id)
	assert found is not None
	assert found.condition is None
	assert found.source is None
	assert found.reading_status is ReadingStatus.TO_READ
