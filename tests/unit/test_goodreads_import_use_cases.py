from datetime import UTC, datetime

import pytest

from app.application.use_cases import (
	AddBookUseCase,
	ConfirmGoodreadsImportInput,
	ConfirmGoodreadsImportItem,
	ConfirmGoodreadsImportSkip,
	ConfirmGoodreadsImportUseCase,
	PreviewGoodreadsImportInput,
	PreviewGoodreadsImportUseCase,
)
from app.domain.entities import BibliographicRecord, OwnedBook, ReadingStatus

_CSV_HEADER = (
	"Book Id,Title,Author,Additional Authors,ISBN,ISBN13,My Rating,Average Rating,"
	"Publisher,Year Published,Original Publication Year,Date Read,Bookshelves,"
	"Exclusive Shelf,My Review\n"
)


def _csv(*rows: str) -> str:
	return _CSV_HEADER + "\n".join(rows)


@pytest.mark.asyncio
async def test_preview_marks_new_row(test_family_id, record_repo, book_repo):
	use_case = PreviewGoodreadsImportUseCase(record_repo, book_repo)

	result = await use_case.execute(
		PreviewGoodreadsImportInput(
			family_id=test_family_id,
			csv_text=_csv('1,Dune,Frank Herbert,,,="9780441013593",5,4.25,Ace,1990,1965,2023/05/12,,read,'),
		)
	)

	assert len(result.rows) == 1
	row = result.rows[0]
	assert row.status == "new"
	assert row.title == "Dune"
	assert row.isbn == "9780441013593"
	assert row.rating == 5
	assert row.read_at == datetime(2023, 5, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_preview_flags_already_owned_by_isbn(test_family_id, record_repo, book_repo):
	record = await record_repo.save(
		BibliographicRecord(family_id=test_family_id, title="Dune", main_author="Frank Herbert", isbn="9780441013593")
	)
	await book_repo.save(OwnedBook(family_id=test_family_id, bibliographic_record_id=record.id))
	use_case = PreviewGoodreadsImportUseCase(record_repo, book_repo)

	result = await use_case.execute(
		PreviewGoodreadsImportInput(
			family_id=test_family_id,
			csv_text=_csv('1,Dune,Frank Herbert,,,="9780441013593",0,4.25,,,,,,to-read,'),
		)
	)

	assert result.rows[0].status == "already_owned"


@pytest.mark.asyncio
async def test_preview_flags_already_owned_by_title_author_when_no_isbn(test_family_id, record_repo, book_repo):
	record = await record_repo.save(
		BibliographicRecord(family_id=test_family_id, title="Dune", main_author="Frank Herbert")
	)
	await book_repo.save(OwnedBook(family_id=test_family_id, bibliographic_record_id=record.id))
	use_case = PreviewGoodreadsImportUseCase(record_repo, book_repo)

	result = await use_case.execute(
		PreviewGoodreadsImportInput(
			family_id=test_family_id, csv_text=_csv("1,Dune,Frank Herbert,,,,0,4.25,,,,,,to-read,")
		)
	)

	assert result.rows[0].status == "already_owned"


@pytest.mark.asyncio
async def test_preview_marks_row_without_title_as_invalid(test_family_id, record_repo, book_repo):
	use_case = PreviewGoodreadsImportUseCase(record_repo, book_repo)

	result = await use_case.execute(
		PreviewGoodreadsImportInput(family_id=test_family_id, csv_text=_csv(",,William Gibson,,,,0,4.0,,,,,,to-read,"))
	)

	assert result.rows[0].status == "invalid"


def _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo):
	add_book = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	return ConfirmGoodreadsImportUseCase(add_book, book_read_repo, book_rating_repo)


@pytest.mark.asyncio
async def test_confirm_creates_books_with_no_physical_position(
	test_family_id, test_user_id, record_repo, book_repo, history_repo, book_read_repo, book_rating_repo
):
	use_case = _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo)

	result = await use_case.execute(
		ConfirmGoodreadsImportInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			items=[
				ConfirmGoodreadsImportItem(
					row_number=1, title="Dune", main_author="Frank Herbert", isbn="9780441013593"
				),
			],
		)
	)

	assert len(result.created_book_ids) == 1
	book = await book_repo.find_by_id(result.created_book_ids[0])
	assert book is not None
	assert book.shelf_id is None
	assert book.room_id is None


@pytest.mark.asyncio
async def test_confirm_attaches_rating_and_review(
	test_family_id, test_user_id, record_repo, book_repo, history_repo, book_read_repo, book_rating_repo
):
	use_case = _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo)

	result = await use_case.execute(
		ConfirmGoodreadsImportInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			items=[
				ConfirmGoodreadsImportItem(row_number=1, title="Dune", rating=5, review="Loved it"),
			],
		)
	)

	assert result.rated_count == 1
	ratings = list(book_rating_repo.ratings.values())
	assert len(ratings) == 1
	assert ratings[0].owned_book_id == result.created_book_ids[0]
	assert ratings[0].user_id == test_user_id
	assert ratings[0].rating == 5
	assert ratings[0].review == "Loved it"


@pytest.mark.asyncio
async def test_confirm_marks_read_with_csv_date_not_now(
	test_family_id, test_user_id, record_repo, book_repo, history_repo, book_read_repo, book_rating_repo
):
	use_case = _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo)
	read_at = datetime(2020, 1, 15, tzinfo=UTC)

	result = await use_case.execute(
		ConfirmGoodreadsImportInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			items=[
				ConfirmGoodreadsImportItem(
					row_number=1, title="Dune", reading_status=ReadingStatus.READ, read_at=read_at
				),
			],
		)
	)

	assert result.read_count == 1
	book = await book_repo.find_by_id(result.created_book_ids[0])
	assert book is not None
	# The stored column never holds READ (it's per-member) — AddBookUseCase
	# collapses it to TO_READ; the actual "read" fact lives in BookReadRepository.
	assert book.reading_status == ReadingStatus.TO_READ
	reads = await book_read_repo.list_by_book(book.id)
	assert len(reads) == 1
	assert reads[0].read_at == read_at


@pytest.mark.asyncio
async def test_confirm_currently_reading_sets_reading_status(
	test_family_id, test_user_id, record_repo, book_repo, history_repo, book_read_repo, book_rating_repo
):
	use_case = _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo)

	result = await use_case.execute(
		ConfirmGoodreadsImportInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			items=[ConfirmGoodreadsImportItem(row_number=1, title="Dune", reading_status=ReadingStatus.READING)],
		)
	)

	book = await book_repo.find_by_id(result.created_book_ids[0])
	assert book is not None
	assert book.reading_status == ReadingStatus.READING
	assert result.read_count == 0


@pytest.mark.asyncio
async def test_confirm_skips_already_owned_without_failing_the_batch(
	test_family_id, test_user_id, record_repo, book_repo, history_repo, book_read_repo, book_rating_repo
):
	record = await record_repo.save(
		BibliographicRecord(family_id=test_family_id, title="Dune", main_author="Frank Herbert")
	)
	await book_repo.save(OwnedBook(family_id=test_family_id, bibliographic_record_id=record.id))
	use_case = _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo)

	result = await use_case.execute(
		ConfirmGoodreadsImportInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			items=[
				ConfirmGoodreadsImportItem(row_number=1, title="Dune", main_author="Frank Herbert"),
				ConfirmGoodreadsImportItem(row_number=2, title="Neuromancer", main_author="William Gibson"),
			],
		)
	)

	assert result.skipped == [ConfirmGoodreadsImportSkip(title="Dune", reason="already_owned", row_number=1)]
	assert len(result.created_book_ids) == 1


@pytest.mark.asyncio
async def test_confirm_skips_the_same_book_appearing_twice_in_one_csv(
	test_family_id, test_user_id, record_repo, book_repo, history_repo, book_read_repo, book_rating_repo
):
	use_case = _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo)

	result = await use_case.execute(
		ConfirmGoodreadsImportInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			items=[
				ConfirmGoodreadsImportItem(row_number=1, title="Dune", isbn="978-0441013593"),
				ConfirmGoodreadsImportItem(row_number=2, title="Dune", isbn="9780441013593"),
			],
		)
	)

	assert len(result.created_book_ids) == 1
	assert result.skipped == [ConfirmGoodreadsImportSkip(title="Dune", reason="duplicate_in_import", row_number=2)]


@pytest.mark.asyncio
async def test_confirm_keeps_intentional_duplicate(
	test_family_id, test_user_id, record_repo, book_repo, history_repo, book_read_repo, book_rating_repo
):
	use_case = _confirm_use_case(record_repo, book_repo, history_repo, book_read_repo, book_rating_repo)

	result = await use_case.execute(
		ConfirmGoodreadsImportInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			items=[
				ConfirmGoodreadsImportItem(row_number=1, title="Dune", isbn="9780441013593"),
				ConfirmGoodreadsImportItem(
					row_number=2, title="Dune", isbn="9780441013593", is_intentional_duplicate=True
				),
			],
		)
	)

	assert len(result.created_book_ids) == 2
	assert result.skipped == []
