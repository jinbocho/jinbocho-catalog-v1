import pytest
from uuid import uuid4

from app.application.use_cases import (
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	GetBibliographicRecordUseCase,
	ListBibliographicRecordsUseCase,
	UpdateBibliographicRecordInput,
	UpdateBibliographicRecordUseCase,
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
	records = await list_use_case.execute(test_family_id, q=None, limit=50, offset=0)

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
	records = await list_use_case.execute(test_family_id, q="Python", limit=50, offset=0)

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
