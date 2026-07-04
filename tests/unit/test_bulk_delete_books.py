from uuid import uuid4

import pytest

from app.application.use_cases.catalog import BulkDeleteBooksInput, BulkDeleteBooksUseCase
from app.domain.entities import OwnedBook
from tests.unit.conftest import MockBookHistoryRepository, MockOwnedBookRepository


async def _seed_book(book_repo: MockOwnedBookRepository, family_id) -> OwnedBook:
	book = OwnedBook(family_id=family_id, bibliographic_record_id=uuid4())
	await book_repo.save(book)
	return book


@pytest.mark.asyncio
async def test_bulk_delete_removes_all_requested_books_and_writes_history() -> None:
	family_id = uuid4()
	changed_by = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	book1 = await _seed_book(book_repo, family_id)
	book2 = await _seed_book(book_repo, family_id)
	book3 = await _seed_book(book_repo, family_id)

	use_case = BulkDeleteBooksUseCase(book_repo, history_repo)
	deleted = await use_case.execute(
		BulkDeleteBooksInput(book_ids=[book1.id, book2.id], family_id=family_id, changed_by=changed_by)
	)

	assert deleted == 2
	assert book_repo.books.keys() == {book3.id}
	history_book_ids = {h.owned_book_id for h in history_repo.history.values()}
	assert history_book_ids == {book1.id, book2.id}


@pytest.mark.asyncio
async def test_bulk_delete_fails_all_or_nothing_when_one_id_missing() -> None:
	family_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	book1 = await _seed_book(book_repo, family_id)
	missing_id = uuid4()

	use_case = BulkDeleteBooksUseCase(book_repo, history_repo)
	with pytest.raises(LookupError):
		await use_case.execute(
			BulkDeleteBooksInput(book_ids=[book1.id, missing_id], family_id=family_id, changed_by=uuid4())
		)

	assert book_repo.books.keys() == {book1.id}
	assert history_repo.history == {}


@pytest.mark.asyncio
async def test_bulk_delete_fails_all_or_nothing_when_one_id_belongs_to_another_family() -> None:
	family_id = uuid4()
	other_family_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	own_book = await _seed_book(book_repo, family_id)
	foreign_book = await _seed_book(book_repo, other_family_id)

	use_case = BulkDeleteBooksUseCase(book_repo, history_repo)
	with pytest.raises(PermissionError):
		await use_case.execute(
			BulkDeleteBooksInput(book_ids=[own_book.id, foreign_book.id], family_id=family_id, changed_by=uuid4())
		)

	assert book_repo.books.keys() == {own_book.id, foreign_book.id}
	assert history_repo.history == {}


@pytest.mark.asyncio
async def test_bulk_delete_dedupes_repeated_ids() -> None:
	family_id = uuid4()
	book_repo = MockOwnedBookRepository()
	history_repo = MockBookHistoryRepository()
	book = await _seed_book(book_repo, family_id)

	use_case = BulkDeleteBooksUseCase(book_repo, history_repo)
	deleted = await use_case.execute(
		BulkDeleteBooksInput(book_ids=[book.id, book.id], family_id=family_id, changed_by=uuid4())
	)

	assert deleted == 1
	assert book_repo.books == {}
	assert len(history_repo.history) == 1
