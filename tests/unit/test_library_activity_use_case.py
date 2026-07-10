from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.use_cases import GetLibraryActivityUseCase
from app.domain.entities import BookEventType, BookHistory


def _entry(event_type: BookEventType, created_at: datetime) -> BookHistory:
	return BookHistory(
		owned_book_id=uuid4(),
		event_type=event_type,
		changed_by=uuid4(),
		created_at=created_at,
	)


@pytest.mark.asyncio
async def test_library_activity_excludes_metadata_updated_and_deleted(history_repo, test_library_id):
	now = datetime.now(UTC)
	await history_repo.save(_entry(BookEventType.CREATED, now))
	await history_repo.save(_entry(BookEventType.METADATA_UPDATED, now - timedelta(minutes=1)))
	await history_repo.save(_entry(BookEventType.DELETED, now - timedelta(minutes=2)))
	await history_repo.save(_entry(BookEventType.POSITION_CHANGED, now - timedelta(minutes=3)))
	await history_repo.save(_entry(BookEventType.READING_STATUS_CHANGED, now - timedelta(minutes=4)))

	result = await GetLibraryActivityUseCase(history_repo).execute(test_library_id)

	event_types = {entry.event_type for entry in result}
	assert event_types == {
		BookEventType.CREATED,
		BookEventType.POSITION_CHANGED,
		BookEventType.READING_STATUS_CHANGED,
	}


@pytest.mark.asyncio
async def test_library_activity_orders_most_recent_first(history_repo, test_library_id):
	now = datetime.now(UTC)
	older = _entry(BookEventType.CREATED, now - timedelta(hours=1))
	newer = _entry(BookEventType.CREATED, now)
	await history_repo.save(older)
	await history_repo.save(newer)

	result = await GetLibraryActivityUseCase(history_repo).execute(test_library_id)

	assert result[0].created_at == newer.created_at
	assert result[1].created_at == older.created_at


@pytest.mark.asyncio
async def test_library_activity_respects_limit(history_repo, test_library_id):
	now = datetime.now(UTC)
	for i in range(5):
		await history_repo.save(_entry(BookEventType.CREATED, now - timedelta(minutes=i)))

	result = await GetLibraryActivityUseCase(history_repo).execute(test_library_id, limit=2)

	assert len(result) == 2
