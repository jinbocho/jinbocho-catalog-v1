from uuid import uuid4

import pytest

from app.application.use_cases import (
	AddBookInput,
	AddBookUseCase,
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	DeleteBibliographicRecordUseCase,
	DuplicateBookError,
	GetBibliographicRecordUseCase,
	ListBibliographicRecordsUseCase,
	UpdateBibliographicRecordInput,
	UpdateBibliographicRecordUseCase,
	UpdateBookMetadataInput,
	UpdateBookMetadataUseCase,
	UpdateReadingStatusInput,
	UpdateReadingStatusUseCase,
)
from app.domain.entities import ReadingStatus


@pytest.mark.asyncio
async def test_create_bibliographic_record(record_repo, test_library_id):
	"""Test creating a bibliographic record."""
	use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		library_id=test_library_id,
		title="Python Design Patterns",
		main_author="John Smith",
		isbn="978-0-13-110362-7",
		publisher="O'Reilly",
		publication_year=2019
	)

	record = await use_case.execute(inp)

	assert record.title == "Python Design Patterns"
	assert record.isbn == "978-0-13-110362-7"
	assert record.library_id == test_library_id


@pytest.mark.asyncio
async def test_create_bibliographic_record_reuses_existing_isbn(record_repo, test_library_id):
	"""Regression: re-submitting the same ISBN used to crash with a generic
	409 'data integrity violation' (UNIQUE(library_id, isbn)) instead of
	reusing the existing record — this is also what makes the add-book
	duplicate-detection flow reachable, since AddBookPage always creates the
	record first and then adds the book against its id."""
	use_case = CreateBibliographicRecordUseCase(record_repo)
	first = await use_case.execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="Dune", isbn="978-0-13-110362-7")
	)

	second = await use_case.execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="Dune (resubmitted)", isbn="978-0-13-110362-7")
	)

	assert second.id == first.id
	assert second.title == "Dune"  # existing record wins, not overwritten


@pytest.mark.asyncio
async def test_get_bibliographic_record(record_repo, test_library_id):
	"""Test retrieving a bibliographic record."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		library_id=test_library_id,
		title="Clean Code",
		main_author="Robert C. Martin",
		isbn="978-0-13-235088-4"
	)

	record = await create_use_case.execute(inp)

	get_use_case = GetBibliographicRecordUseCase(record_repo)
	retrieved = await get_use_case.execute(record.id, test_library_id)

	assert retrieved.id == record.id
	assert retrieved.title == "Clean Code"


@pytest.mark.asyncio
async def test_get_bibliographic_record_not_found(record_repo, test_library_id):
	"""Test getting a non-existent record."""
	use_case = GetBibliographicRecordUseCase(record_repo)

	with pytest.raises(LookupError):
		await use_case.execute(uuid4(), test_library_id)


@pytest.mark.asyncio
async def test_list_bibliographic_records(record_repo, test_library_id):
	"""Test listing bibliographic records."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)

	# Create 3 records
	for i in range(3):
		inp = CreateBibliographicRecordInput(
			library_id=test_library_id,
			title=f"Book {i}",
			main_author="Author"
		)
		await create_use_case.execute(inp)

	list_use_case = ListBibliographicRecordsUseCase(record_repo)
	records = await list_use_case.execute(test_library_id, q=None, genre=None, limit=50, offset=0)

	assert len(records) == 3


@pytest.mark.asyncio
async def test_list_bibliographic_records_search(record_repo, test_library_id):
	"""Test searching bibliographic records."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)

	# Create records with different titles
	titles = ["Python Programming", "Java Basics", "Python Design Patterns"]
	for title in titles:
		inp = CreateBibliographicRecordInput(
			library_id=test_library_id,
			title=title,
			main_author="Author"
		)
		await create_use_case.execute(inp)

	list_use_case = ListBibliographicRecordsUseCase(record_repo)
	records = await list_use_case.execute(test_library_id, q="Python", genre=None, limit=50, offset=0)

	assert len(records) == 2


@pytest.mark.asyncio
async def test_update_bibliographic_record(record_repo, test_library_id):
	"""Test updating a bibliographic record."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		library_id=test_library_id,
		title="Old Title",
		main_author="Old Author"
	)
	record = await create_use_case.execute(inp)

	update_use_case = UpdateBibliographicRecordUseCase(record_repo)
	update_inp = UpdateBibliographicRecordInput(
		record_id=record.id,
		library_id=test_library_id,
		title="New Title",
		main_author="New Author"
	)
	updated = await update_use_case.execute(update_inp)

	assert updated.title == "New Title"
	assert updated.main_author == "New Author"


@pytest.mark.asyncio
async def test_delete_bibliographic_record(record_repo, book_repo, test_library_id):
	"""Test deleting a bibliographic record."""
	create_use_case = CreateBibliographicRecordUseCase(record_repo)
	inp = CreateBibliographicRecordInput(
		library_id=test_library_id,
		title="To Delete",
		main_author="Author"
	)
	record = await create_use_case.execute(inp)

	delete_use_case = DeleteBibliographicRecordUseCase(record_repo, book_repo)
	await delete_use_case.execute(record.id, test_library_id)

	# Verify it's deleted
	get_use_case = GetBibliographicRecordUseCase(record_repo)
	with pytest.raises(LookupError):
		await get_use_case.execute(record.id, test_library_id)


@pytest.mark.asyncio
async def test_add_book_with_reading_status_sets_current_reader(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""Adding a book already marked as 'reading' must set current_reader_id
	(regression: this used to be silently left null, hiding who's reading it)."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	inp = AddBookInput(
		library_id=test_library_id,
		changed_by=test_user_id,
		title="The Hobbit",
		reading_status=ReadingStatus.READING,
	)

	book = await use_case.execute(inp)

	assert book.reading_status is ReadingStatus.READING
	assert book.current_reader_id == test_user_id


@pytest.mark.asyncio
async def test_add_book_read_records_a_per_member_book_read(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""Adding a book already marked 'read' must record it as read by the
	creator only — not as a library-wide status everyone else inherits."""
	other_user_id = uuid4()
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	inp = AddBookInput(
		library_id=test_library_id,
		changed_by=test_user_id,
		title="The Hobbit",
		reading_status=ReadingStatus.READ,
	)

	book = await use_case.execute(inp)

	assert book.reading_status is ReadingStatus.READ
	assert await book_read_repo.is_read(book.id, test_user_id) is True
	assert await book_read_repo.is_read(book.id, other_user_id) is False


@pytest.mark.asyncio
async def test_add_book_to_read_has_no_current_reader(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""Default 'to_read' status must not assign a reader."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	inp = AddBookInput(
		library_id=test_library_id,
		changed_by=test_user_id,
		title="The Hobbit",
	)

	book = await use_case.execute(inp)

	assert book.current_reader_id is None


@pytest.mark.asyncio
async def test_add_book_detects_isbn_duplicate(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""Adding a second copy with an ISBN the library already has must be
	flagged rather than silently created."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	await use_case.execute(
		AddBookInput(
			library_id=test_library_id, changed_by=test_user_id, title="Dune",
			isbn="9780441013593", owner_id=test_user_id,
		)
	)

	with pytest.raises(DuplicateBookError) as exc_info:
		await use_case.execute(
			AddBookInput(library_id=test_library_id, changed_by=test_user_id, title="Dune", isbn="9780441013593")
		)

	assert exc_info.value.conflict.conflict_type == "isbn_match"


@pytest.mark.asyncio
async def test_add_book_detects_isbn_duplicate_even_with_a_different_owner(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""The check is library-wide, not owner-scoped: a different library member
	can still confirm-and-add a second copy, but the system must warn first
	rather than silently assume two owners means it's never a duplicate."""
	other_owner_id = uuid4()
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	await use_case.execute(
		AddBookInput(
			library_id=test_library_id, changed_by=test_user_id, title="Dune",
			isbn="9780441013593", owner_id=test_user_id,
		)
	)

	with pytest.raises(DuplicateBookError):
		await use_case.execute(
			AddBookInput(
				library_id=test_library_id, changed_by=test_user_id, title="Dune",
				isbn="9780441013593", owner_id=other_owner_id,
			)
		)


@pytest.mark.asyncio
async def test_add_book_duplicate_conflict_reports_existing_owner_and_location(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""The conflict must surface who already has the book and where, so the
	confirm dialog can show it instead of just blocking blindly."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	room_id, bookcase_id, section_id, shelf_id = uuid4(), uuid4(), uuid4(), uuid4()
	first = await use_case.execute(
		AddBookInput(
			library_id=test_library_id, changed_by=test_user_id, title="Dune", isbn="9780441013593",
			owner_id=test_user_id, room_id=room_id, bookcase_id=bookcase_id,
			section_id=section_id, shelf_id=shelf_id,
		)
	)

	with pytest.raises(DuplicateBookError) as exc_info:
		await use_case.execute(
			AddBookInput(library_id=test_library_id, changed_by=test_user_id, title="Dune", isbn="9780441013593")
		)

	conflict = exc_info.value.conflict
	assert conflict.existing_book_id == first.id
	assert conflict.existing_owner_id == test_user_id
	assert conflict.existing_room_id == room_id
	assert conflict.existing_bookcase_id == bookcase_id
	assert conflict.existing_section_id == section_id
	assert conflict.existing_shelf_id == shelf_id


@pytest.mark.asyncio
async def test_add_book_detects_title_author_duplicate_across_different_isbns(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""Same title/author but a different (or missing) ISBN — e.g. added twice
	under two different editions — must still be flagged."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	await use_case.execute(
		AddBookInput(library_id=test_library_id, changed_by=test_user_id, title="Dune", main_author="Frank Herbert")
	)

	with pytest.raises(DuplicateBookError) as exc_info:
		await use_case.execute(
			AddBookInput(
				library_id=test_library_id, changed_by=test_user_id, title="Dune", main_author="Frank Herbert",
				isbn="9780441013593",
			)
		)

	assert exc_info.value.conflict.conflict_type == "title_author_match"


@pytest.mark.asyncio
async def test_add_book_intentional_duplicate_bypasses_the_check(
	record_repo, book_repo, history_repo, book_read_repo, test_library_id, test_user_id
):
	"""The user confirmed they want a second copy — is_intentional_duplicate=True
	skips the check and is persisted on the new book."""
	use_case = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	await use_case.execute(
		AddBookInput(
			library_id=test_library_id, changed_by=test_user_id, title="Dune",
			isbn="9780441013593", owner_id=test_user_id,
		)
	)

	book = await use_case.execute(
		AddBookInput(
			library_id=test_library_id, changed_by=test_user_id, title="Dune", isbn="9780441013593",
			owner_id=test_user_id, is_intentional_duplicate=True,
		)
	)

	assert book.is_intentional_duplicate is True


@pytest.mark.asyncio
async def test_update_reading_status_sets_and_clears_current_reader(
	book_repo, book_read_repo, book_abandonment_repo, history_repo, test_library_id, test_user_id
):
	"""Switching to 'reading' assigns the current reader; switching away clears it."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	book = await book_repo.save(
		OwnedBook(
			library_id=test_library_id,
			bibliographic_record_id=uuid4(),
			reading_status=ReadingStatus.TO_READ,
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)

	use_case = UpdateReadingStatusUseCase(book_repo, book_read_repo, history_repo, book_abandonment_repo)
	updated = await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.READING
		)
	)
	assert updated.current_reader_id == test_user_id

	updated = await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.READ
		)
	)
	assert updated.current_reader_id is None


@pytest.mark.asyncio
async def test_reading_status_for_shows_reading_to_every_member(
	book_repo, book_read_repo, book_abandonment_repo, history_repo, test_library_id, test_user_id
):
	"""Regression: unlike "read", "reading" reflects who's physically holding
	the single copy — every other library member must see it too, not just
	the holder (the bug: reading_status_for used to gate READING on
	viewer_id == current_reader_id, so a parent's dashboard "currently
	reading" list silently excluded every book a child was reading)."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	other_user_id = uuid4()
	book = await book_repo.save(
		OwnedBook(
			library_id=test_library_id,
			bibliographic_record_id=uuid4(),
			reading_status=ReadingStatus.TO_READ,
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)

	use_case = UpdateReadingStatusUseCase(book_repo, book_read_repo, history_repo, book_abandonment_repo)
	updated = await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.READING
		)
	)

	other_has_read = await book_read_repo.is_read(book.id, other_user_id)
	assert updated.reading_status_for(other_has_read) == ReadingStatus.READING


@pytest.mark.asyncio
async def test_update_reading_status_read_is_per_member(
	book_repo, book_read_repo, book_abandonment_repo, history_repo, test_library_id, test_user_id
):
	"""Regression: one member marking a book read must not flip it to "read"
	for every other library member — only their own BookRead row changes."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	other_user_id = uuid4()
	book = await book_repo.save(
		OwnedBook(
			library_id=test_library_id,
			bibliographic_record_id=uuid4(),
			reading_status=ReadingStatus.TO_READ,
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)

	use_case = UpdateReadingStatusUseCase(book_repo, book_read_repo, history_repo, book_abandonment_repo)
	updated = await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.READ
		)
	)

	# The caller sees "read"...
	caller_has_read = await book_read_repo.is_read(book.id, test_user_id)
	assert updated.reading_status_for(caller_has_read) == ReadingStatus.READ
	# ...but another library member who hasn't read it still sees "to_read".
	other_has_read = await book_read_repo.is_read(book.id, other_user_id)
	assert updated.reading_status_for(other_has_read) == ReadingStatus.TO_READ


@pytest.mark.asyncio
async def test_update_book_metadata_reading_status_sets_current_reader(
	book_repo, book_read_repo, book_abandonment_repo, history_repo, test_library_id, test_user_id
):
	"""The generic metadata-update path must mirror the same current_reader_id rule
	as the dedicated reading-status endpoint (regression: it didn't)."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	book = await book_repo.save(
		OwnedBook(
			library_id=test_library_id,
			bibliographic_record_id=uuid4(),
			reading_status=ReadingStatus.TO_READ,
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)

	use_case = UpdateBookMetadataUseCase(book_repo, book_read_repo, history_repo, book_abandonment_repo)
	updated = await use_case.execute(
		UpdateBookMetadataInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.READING
		)
	)

	assert updated.current_reader_id == test_user_id


@pytest.mark.asyncio
async def test_update_reading_status_abandon_is_per_member(
	book_repo, book_read_repo, book_abandonment_repo, history_repo, test_library_id, test_user_id
):
	"""KID-05: abandoning a book is a per-member fact, like 'read' — it must
	never change what another library member sees for the same copy."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	other_user_id = uuid4()
	book = await book_repo.save(
		OwnedBook(
			library_id=test_library_id,
			bibliographic_record_id=uuid4(),
			reading_status=ReadingStatus.TO_READ,
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)

	use_case = UpdateReadingStatusUseCase(book_repo, book_read_repo, history_repo, book_abandonment_repo)
	updated = await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.ABANDONED
		)
	)

	caller_has_abandoned = await book_abandonment_repo.is_abandoned(book.id, test_user_id)
	assert updated.reading_status_for(False, caller_has_abandoned) == ReadingStatus.ABANDONED
	other_has_abandoned = await book_abandonment_repo.is_abandoned(book.id, other_user_id)
	assert updated.reading_status_for(False, other_has_abandoned) == ReadingStatus.TO_READ


@pytest.mark.asyncio
async def test_update_reading_status_abandoned_and_read_are_mutually_exclusive(
	book_repo, book_read_repo, book_abandonment_repo, history_repo, test_library_id, test_user_id
):
	"""Marking a previously-abandoned book as read clears the abandoned mark,
	and vice versa — a book is never both for the same reader."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	book = await book_repo.save(
		OwnedBook(
			library_id=test_library_id,
			bibliographic_record_id=uuid4(),
			reading_status=ReadingStatus.TO_READ,
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)
	use_case = UpdateReadingStatusUseCase(book_repo, book_read_repo, history_repo, book_abandonment_repo)

	await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.ABANDONED
		)
	)
	assert await book_abandonment_repo.is_abandoned(book.id, test_user_id) is True

	await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.READ
		)
	)
	assert await book_abandonment_repo.is_abandoned(book.id, test_user_id) is False
	assert await book_read_repo.is_read(book.id, test_user_id) is True

	await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.ABANDONED
		)
	)
	assert await book_read_repo.is_read(book.id, test_user_id) is False
	assert await book_abandonment_repo.is_abandoned(book.id, test_user_id) is True


@pytest.mark.asyncio
async def test_picking_up_an_abandoned_book_again_clears_the_abandoned_mark(
	book_repo, book_read_repo, book_abandonment_repo, history_repo, test_library_id, test_user_id
):
	"""Re-reading a previously abandoned book (KID-05's 'rileggere conta')
	starting it again is a fresh attempt, not a lingering abandoned mark."""
	from app.domain.entities import OwnedBook
	from app.utils import utcnow

	book = await book_repo.save(
		OwnedBook(
			library_id=test_library_id,
			bibliographic_record_id=uuid4(),
			reading_status=ReadingStatus.TO_READ,
			created_at=utcnow(),
			updated_at=utcnow(),
		)
	)
	use_case = UpdateReadingStatusUseCase(book_repo, book_read_repo, history_repo, book_abandonment_repo)

	await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.ABANDONED
		)
	)
	await use_case.execute(
		UpdateReadingStatusInput(
			book_id=book.id, library_id=test_library_id, changed_by=test_user_id, reading_status=ReadingStatus.READING
		)
	)

	assert await book_abandonment_repo.is_abandoned(book.id, test_user_id) is False
