import pytest
from uuid import uuid4

from app.application.use_cases import (
	AddBookInput,
	AddBookUseCase,
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	GetBibliographicRecordUseCase,
	ListBibliographicRecordsUseCase,
	UpdateBibliographicRecordInput,
	UpdateBibliographicRecordUseCase,
	UpdateBookMetadataInput,
	UpdateBookMetadataUseCase,
	UpdateReadingStatusInput,
	UpdateReadingStatusUseCase,
	DeleteBibliographicRecordUseCase,
	ListOwnedBooksUseCase,
)


@pytest.mark.asyncio
async def test_create_bibliographic_record(record_repo, test_family_id):
	"""Test creating a bibliographic record."""
	use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		family_id=test_family_id,
		title="Python Design Patterns",
		main_author="John Smith",
		isbn="978-0-13-110362-7",
		publisher="O'Reilly",
		publication_year=2019
	)

	record = await use_case.execute(inp)

	assert record.title == "Python Design Patterns"
	assert record.isbn == "978-0-13-110362-7"
	assert record.family_id == test_family_id


@pytest.mark.asyncio
async def test_get_bibliographic_record(record_repo, test_family_id):
	"""Test retrieving a bibliographic record."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		family_id=test_family_id,
		title="Clean Code",
		main_author="Robert C. Martin",
		isbn="978-0-13-235088-4"
	)

	record = await create_use_case.execute(inp)

	get_use_case = GetBibliographicRecordUseCase(record_repo)
	retrieved = await get_use_case.execute(record.id, test_family_id)

	assert retrieved.id == record.id
	assert retrieved.title == "Clean Code"


@pytest.mark.asyncio
async def test_get_bibliographic_record_not_found(record_repo, test_family_id):
	"""Test getting a non-existent record."""
	use_case = GetBibliographicRecordUseCase(record_repo)

	with pytest.raises(LookupError):
		await use_case.execute(uuid4(), test_family_id)


@pytest.mark.asyncio
async def test_list_bibliographic_records(record_repo, test_family_id):
	"""Test listing bibliographic records."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)

	# Create 3 records
	for i in range(3):
		inp = CreateBibliographicRecordInput(
			family_id=test_family_id,
			title=f"Book {i}",
			main_author="Author"
		)
		await create_use_case.execute(inp)

	list_use_case = ListBibliographicRecordsUseCase(record_repo)
	records = await list_use_case.execute(test_family_id, q=None, genre=None, limit=50, offset=0)

	assert len(records) == 3


@pytest.mark.asyncio
async def test_list_bibliographic_records_search(record_repo, test_family_id):
	"""Test searching bibliographic records."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)

	# Create records with different titles
	titles = ["Python Programming", "Java Basics", "Python Design Patterns"]
	for title in titles:
		inp = CreateBibliographicRecordInput(
			family_id=test_family_id,
			title=title,
			main_author="Author"
		)
		await create_use_case.execute(inp)

	list_use_case = ListBibliographicRecordsUseCase(record_repo)
	records = await list_use_case.execute(test_family_id, q="Python", genre=None, limit=50, offset=0)

	assert len(records) == 2


@pytest.mark.asyncio
async def test_update_bibliographic_record(record_repo, test_family_id):
	"""Test updating a bibliographic record."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		family_id=test_family_id,
		title="Old Title",
		main_author="Old Author"
	)
	record = await create_use_case.execute(inp)

	update_use_case = UpdateBibliographicRecordUseCase(record_repo)
	update_inp = UpdateBibliographicRecordInput(
		record_id=record.id,
		family_id=test_family_id,
		title="New Title",
		main_author="New Author"
	)
	updated = await update_use_case.execute(update_inp)

	assert updated.title == "New Title"
	assert updated.main_author == "New Author"


@pytest.mark.asyncio
async def test_delete_bibliographic_record(record_repo, book_repo, test_family_id):
	"""Test deleting a bibliographic record."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		family_id=test_family_id,
		title="To Delete",
		main_author="Author"
	)
	record = await create_use_case.execute(inp)

	delete_use_case = DeleteBibliographicRecordUseCase(record_repo, book_repo)
	await delete_use_case.execute(record.id, test_family_id)

	# Verify it's deleted
	get_use_case = GetBibliographicRecordUseCase(record_repo)
	with pytest.raises(LookupError):
		await get_use_case.execute(record.id, test_family_id)


@pytest.mark.asyncio
async def test_add_book_with_reading_status_sets_current_reader(
	record_repo, book_repo, history_repo, cache_repo, test_family_id, test_user_id
):
	"""Adding a book already marked as 'reading' must set current_reader_id
	(regression: this used to be silently left null, hiding who's reading it)."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, cache_repo)
	inp = AddBookInput(
		family_id=test_family_id,
		changed_by=test_user_id,
		title="The Hobbit",
		reading_status="reading",
	)

	book = await use_case.execute(inp)

	assert book.reading_status == "reading"
	assert book.current_reader_id == test_user_id


@pytest.mark.asyncio
async def test_add_book_to_read_has_no_current_reader(
	record_repo, book_repo, history_repo, cache_repo, test_family_id, test_user_id
):
	"""Default 'to_read' status must not assign a reader."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, cache_repo)
	inp = AddBookInput(
		family_id=test_family_id,
		changed_by=test_user_id,
		title="The Hobbit",
	)

	book = await use_case.execute(inp)

	assert book.current_reader_id is None


@pytest.mark.asyncio
async def test_update_reading_status_sets_and_clears_current_reader(book_repo, history_repo, test_family_id, test_user_id):
	"""Switching to 'reading' assigns the current reader; switching away clears it."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	book = await book_repo.save(
		OwnedBook(
			family_id=test_family_id,
			bibliographic_record_id=uuid4(),
			reading_status="to_read",
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)

	use_case = UpdateReadingStatusUseCase(book_repo, history_repo)
	updated = await use_case.execute(
		UpdateReadingStatusInput(book_id=book.id, family_id=test_family_id, changed_by=test_user_id, reading_status="reading")
	)
	assert updated.current_reader_id == test_user_id

	updated = await use_case.execute(
		UpdateReadingStatusInput(book_id=book.id, family_id=test_family_id, changed_by=test_user_id, reading_status="read")
	)
	assert updated.current_reader_id is None


@pytest.mark.asyncio
async def test_update_book_metadata_reading_status_sets_current_reader(book_repo, history_repo, test_family_id, test_user_id):
	"""The generic metadata-update path must mirror the same current_reader_id rule
	as the dedicated reading-status endpoint (regression: it didn't)."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	book = await book_repo.save(
		OwnedBook(
			family_id=test_family_id,
			bibliographic_record_id=uuid4(),
			reading_status="to_read",
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)

	use_case = UpdateBookMetadataUseCase(book_repo, history_repo)
	updated = await use_case.execute(
		UpdateBookMetadataInput(book_id=book.id, family_id=test_family_id, changed_by=test_user_id, reading_status="reading")
	)

	assert updated.current_reader_id == test_user_id
