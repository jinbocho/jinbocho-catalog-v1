from uuid import uuid4

import pytest

from app.application.use_cases.catalog import BulkMoveBooksInput, BulkMoveBooksUseCase
from app.domain.entities import OwnedBook
from tests.unit.conftest import MockBookHistoryRepository, MockOwnedBookRepository


async def _seed_book(book_repo: MockOwnedBookRepository, library_id) -> OwnedBook:
	book = OwnedBook(library_id=library_id, bibliographic_record_id=uuid4())
	await book_repo.save(book)
	return book


@pytest.mark.asyncio
async def test_bulk_move_updates_position_for_all_requested_books_and_writes_history() -> None:
	library_id = uuid4()
	changed_by = uuid4()
	room_id = uuid4()
	bookcase_id = uuid4()
	section_id = uuid4()
	shelf_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	book1 = await _seed_book(book_repo, library_id)
	book2 = await _seed_book(book_repo, library_id)
	book3 = await _seed_book(book_repo, library_id)

	use_case = BulkMoveBooksUseCase(book_repo, history_repo)
	moved = await use_case.execute(
		BulkMoveBooksInput(
			book_ids=[book1.id, book2.id],
			library_id=library_id,
			changed_by=changed_by,
			room_id=room_id,
			bookcase_id=bookcase_id,
			section_id=section_id,
			shelf_id=shelf_id,
			shelf_position=None,
		)
	)

	assert moved == 2
	assert book_repo.books[book1.id].room_id == room_id
	assert book_repo.books[book1.id].shelf_id == shelf_id
	assert book_repo.books[book2.id].room_id == room_id
	assert book_repo.books[book3.id].room_id is None
	history_book_ids = {h.owned_book_id for h in history_repo.history.values()}
	assert history_book_ids == {book1.id, book2.id}


@pytest.mark.asyncio
async def test_bulk_move_fails_all_or_nothing_when_one_id_missing() -> None:
	library_id = uuid4()
	room_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	book1 = await _seed_book(book_repo, library_id)
	missing_id = uuid4()

	use_case = BulkMoveBooksUseCase(book_repo, history_repo)
	with pytest.raises(LookupError):
		await use_case.execute(
			BulkMoveBooksInput(
				book_ids=[book1.id, missing_id],
				library_id=library_id,
				changed_by=uuid4(),
				room_id=room_id,
				bookcase_id=None,
				section_id=None,
				shelf_id=None,
				shelf_position=None,
			)
		)

	assert book_repo.books[book1.id].room_id is None
	assert history_repo.history == {}


@pytest.mark.asyncio
async def test_bulk_move_fails_all_or_nothing_when_one_id_belongs_to_another_library() -> None:
	library_id = uuid4()
	other_library_id = uuid4()
	room_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	own_book = await _seed_book(book_repo, library_id)
	foreign_book = await _seed_book(book_repo, other_library_id)

	use_case = BulkMoveBooksUseCase(book_repo, history_repo)
	with pytest.raises(PermissionError):
		await use_case.execute(
			BulkMoveBooksInput(
				book_ids=[own_book.id, foreign_book.id],
				library_id=library_id,
				changed_by=uuid4(),
				room_id=room_id,
				bookcase_id=None,
				section_id=None,
				shelf_id=None,
				shelf_position=None,
			)
		)

	assert book_repo.books[own_book.id].room_id is None
	assert history_repo.history == {}


@pytest.mark.asyncio
async def test_bulk_move_dedupes_repeated_ids() -> None:
	library_id = uuid4()
	room_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	book = await _seed_book(book_repo, library_id)

	use_case = BulkMoveBooksUseCase(book_repo, history_repo)
	moved = await use_case.execute(
		BulkMoveBooksInput(
			book_ids=[book.id, book.id],
			library_id=library_id,
			changed_by=uuid4(),
			room_id=room_id,
			bookcase_id=None,
			section_id=None,
			shelf_id=None,
			shelf_position=None,
		)
	)

	assert moved == 1
	assert book_repo.books[book.id].room_id == room_id
	assert len(history_repo.history) == 1


@pytest.mark.asyncio
async def test_bulk_move_can_clear_position() -> None:
	library_id = uuid4()
	room_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	book = await _seed_book(book_repo, library_id)
	book.room_id = room_id
	await book_repo.save(book)

	use_case = BulkMoveBooksUseCase(book_repo, history_repo)
	moved = await use_case.execute(
		BulkMoveBooksInput(
			book_ids=[book.id],
			library_id=library_id,
			changed_by=uuid4(),
			room_id=None,
			bookcase_id=None,
			section_id=None,
			shelf_id=None,
			shelf_position=None,
		)
	)

	assert moved == 1
	assert book_repo.books[book.id].room_id is None
