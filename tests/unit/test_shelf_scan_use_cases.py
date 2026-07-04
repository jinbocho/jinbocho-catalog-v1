from typing import Any
from uuid import UUID, uuid4

import pytest

from app.application.use_cases import (
	AddBookUseCase,
	AuditShelfInput,
	AuditShelfUseCase,
	ConfirmShelfScanInput,
	ConfirmShelfScanItem,
	ConfirmShelfScanSkip,
	ConfirmShelfScanUseCase,
	ScanShelfInput,
	ScanShelfUseCase,
)
from app.domain.entities import BibliographicRecord, Bookcase, OwnedBook, Room, Section, Shelf
from app.domain.repositories import BookSearchProvider, ShelfSpineReader, SpineReading, SpineReadResult


class StubSpineReader(ShelfSpineReader):
	def __init__(self, spines: list[SpineReading] | None, reason: str = "ok") -> None:
		# spines=None models an unavailable read carrying the given reason.
		if spines is None:
			self._result = SpineReadResult(available=False, reason=reason)
		else:
			self._result = SpineReadResult(available=True, reason="ok", spines=spines)

	async def read_spines(self, image_base64: str, media_type: str) -> SpineReadResult:
		return self._result


class StubSearchProvider(BookSearchProvider):
	def __init__(self, results: list[dict[str, Any]]) -> None:
		self._results = results

	async def search(self, title: str | None, author: str | None, max_results: int) -> list[dict[str, Any]]:
		return self._results


async def _build_shelf(family_id: UUID, room_repo, bookcase_repo, section_repo, shelf_repo) -> Shelf:
	room = await room_repo.save(Room(family_id=family_id, name="Studio"))
	bookcase = await bookcase_repo.save(Bookcase(family_id=family_id, room_id=room.id, name="Billy"))
	section = await section_repo.save(Section(bookcase_id=bookcase.id, section_index=1))
	return await shelf_repo.save(Shelf(section_id=section.id, shelf_index=1))


def _scan_use_case(shelf_repo, section_repo, bookcase_repo, reader, provider, record_repo, book_repo):
	return ScanShelfUseCase(shelf_repo, section_repo, bookcase_repo, reader, provider, record_repo, book_repo)


@pytest.mark.asyncio
async def test_scan_reports_unavailable_when_vision_is_off(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _scan_use_case(
		shelf_repo, section_repo, bookcase_repo, StubSpineReader(None, reason="unsupported"),
		StubSearchProvider([]), record_repo, book_repo
	)

	result = await use_case.execute(
		ScanShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
	)

	assert result.available is False
	assert result.candidates == []
	assert result.reason == "unsupported"  # propagated from the reader for an accurate FE message


@pytest.mark.asyncio
async def test_scan_matches_a_spine_against_the_provider(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	reader = StubSpineReader([SpineReading(title="Dune", author="Frank Herbert", position=0)])
	provider = StubSearchProvider([{"title": "Dune", "main_author": "Frank Herbert", "isbn": "9780441013593"}])
	use_case = _scan_use_case(shelf_repo, section_repo, bookcase_repo, reader, provider, record_repo, book_repo)

	result = await use_case.execute(
		ScanShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
	)

	assert result.available is True
	assert len(result.candidates) == 1
	candidate = result.candidates[0]
	assert candidate.status == "matched"
	assert candidate.metadata is not None
	assert candidate.metadata["isbn"] == "9780441013593"
	assert candidate.already_owned is False


@pytest.mark.asyncio
async def test_scan_flags_weak_provider_hit_as_uncertain(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	reader = StubSpineReader([SpineReading(title="Il nome della rosa", author=None, position=0)])
	provider = StubSearchProvider([{"title": "Il nome della rosa e altri scritti", "main_author": "Umberto Eco"}])
	use_case = _scan_use_case(shelf_repo, section_repo, bookcase_repo, reader, provider, record_repo, book_repo)

	result = await use_case.execute(
		ScanShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
	)

	assert result.candidates[0].status == "uncertain"
	assert result.candidates[0].metadata is not None


@pytest.mark.asyncio
async def test_scan_marks_spine_not_found_when_provider_has_nothing(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	reader = StubSpineReader([SpineReading(title="Titolo Illeggibile", author=None, position=0)])
	use_case = _scan_use_case(
		shelf_repo, section_repo, bookcase_repo, reader, StubSearchProvider([]), record_repo, book_repo
	)

	result = await use_case.execute(
		ScanShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
	)

	assert result.candidates[0].status == "not_found"
	assert result.candidates[0].metadata is None


@pytest.mark.asyncio
async def test_scan_flags_books_the_family_already_owns(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	record = await record_repo.save(
		BibliographicRecord(family_id=test_family_id, title="Dune", main_author="Frank Herbert")
	)
	await book_repo.save(OwnedBook(family_id=test_family_id, bibliographic_record_id=record.id))
	reader = StubSpineReader([SpineReading(title="Dune", author="Frank Herbert", position=0)])
	provider = StubSearchProvider([{"title": "Dune", "main_author": "Frank Herbert"}])
	use_case = _scan_use_case(shelf_repo, section_repo, bookcase_repo, reader, provider, record_repo, book_repo)

	result = await use_case.execute(
		ScanShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
	)

	assert result.candidates[0].already_owned is True


@pytest.mark.asyncio
async def test_scan_rejects_a_shelf_of_another_family(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	other_family = uuid4()
	shelf = await _build_shelf(other_family, room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _scan_use_case(
		shelf_repo, section_repo, bookcase_repo, StubSpineReader([]), StubSearchProvider([]), record_repo, book_repo
	)

	with pytest.raises(PermissionError):
		await use_case.execute(
			ScanShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
		)


@pytest.mark.asyncio
async def test_scan_rejects_unknown_shelf(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	use_case = _scan_use_case(
		shelf_repo, section_repo, bookcase_repo, StubSpineReader([]), StubSearchProvider([]), record_repo, book_repo
	)

	with pytest.raises(LookupError):
		await use_case.execute(
			ScanShelfInput(family_id=test_family_id, shelf_id=uuid4(), image_base64="abc", media_type="image/jpeg")
		)


def _confirm_use_case(shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo):
	add_book = AddBookUseCase(record_repo, book_repo, history_repo, book_read_repo)
	return ConfirmShelfScanUseCase(shelf_repo, section_repo, bookcase_repo, book_repo, add_book)


@pytest.mark.asyncio
async def test_confirm_creates_books_positioned_on_the_scanned_shelf(
	test_family_id, test_user_id, room_repo, bookcase_repo, section_repo, shelf_repo,
	record_repo, book_repo, history_repo, book_read_repo,
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _confirm_use_case(
		shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo
	)

	result = await use_case.execute(
		ConfirmShelfScanInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			shelf_id=shelf.id,
			items=[
				ConfirmShelfScanItem(title="Dune", main_author="Frank Herbert", isbn="9780441013593"),
				ConfirmShelfScanItem(title="Neuromancer", main_author="William Gibson"),
			],
		)
	)

	assert len(result.created_book_ids) == 2
	assert result.skipped == []
	books = sorted(book_repo.books.values(), key=lambda b: b.shelf_position or 0)
	assert [b.shelf_position for b in books] == [1, 2]
	assert all(b.shelf_id == shelf.id for b in books)
	assert all(b.section_id is not None and b.bookcase_id is not None and b.room_id is not None for b in books)


@pytest.mark.asyncio
async def test_confirm_orders_books_by_spine_position_not_list_order(
	test_family_id, test_user_id, room_repo, bookcase_repo, section_repo, shelf_repo,
	record_repo, book_repo, history_repo, book_read_repo,
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _confirm_use_case(
		shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo
	)

	# Sent out of order; the spine positions must drive shelf placement.
	result = await use_case.execute(
		ConfirmShelfScanInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			shelf_id=shelf.id,
			items=[
				ConfirmShelfScanItem(title="Third", position=2),
				ConfirmShelfScanItem(title="First", position=0),
				ConfirmShelfScanItem(title="Second", position=1),
			],
		)
	)

	assert len(result.created_book_ids) == 3
	placed = sorted(book_repo.books.values(), key=lambda b: b.shelf_position or 0)
	titles = [
		(await record_repo.find_by_id(b.bibliographic_record_id)).title  # type: ignore[union-attr]
		for b in placed
	]
	assert titles == ["First", "Second", "Third"]
	assert [b.shelf_position for b in placed] == [1, 2, 3]


@pytest.mark.asyncio
async def test_confirm_positions_after_books_already_on_the_shelf(
	test_family_id, test_user_id, room_repo, bookcase_repo, section_repo, shelf_repo,
	record_repo, book_repo, history_repo, book_read_repo,
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	existing_record = await record_repo.save(BibliographicRecord(family_id=test_family_id, title="Fondazione"))
	await book_repo.save(
		OwnedBook(
			family_id=test_family_id,
			bibliographic_record_id=existing_record.id,
			shelf_id=shelf.id,
			shelf_position=4,
		)
	)
	use_case = _confirm_use_case(
		shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo
	)

	result = await use_case.execute(
		ConfirmShelfScanInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			shelf_id=shelf.id,
			items=[ConfirmShelfScanItem(title="Dune")],
		)
	)

	created = await book_repo.find_by_id(result.created_book_ids[0])
	assert created is not None
	assert created.shelf_position == 5


@pytest.mark.asyncio
async def test_confirm_skips_duplicates_without_failing_the_batch(
	test_family_id, test_user_id, room_repo, bookcase_repo, section_repo, shelf_repo,
	record_repo, book_repo, history_repo, book_read_repo,
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	record = await record_repo.save(
		BibliographicRecord(family_id=test_family_id, title="Dune", main_author="Frank Herbert")
	)
	await book_repo.save(OwnedBook(family_id=test_family_id, bibliographic_record_id=record.id))
	use_case = _confirm_use_case(
		shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo
	)

	result = await use_case.execute(
		ConfirmShelfScanInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			shelf_id=shelf.id,
			items=[
				ConfirmShelfScanItem(title="Dune", main_author="Frank Herbert"),
				ConfirmShelfScanItem(title="Neuromancer", main_author="William Gibson"),
			],
		)
	)

	assert result.skipped == [ConfirmShelfScanSkip(title="Dune", reason="already_owned", position=0)]
	assert len(result.created_book_ids) == 1


@pytest.mark.asyncio
async def test_confirm_skips_the_same_book_matched_twice_in_one_scan(
	test_family_id, test_user_id, room_repo, bookcase_repo, section_repo, shelf_repo,
	record_repo, book_repo, history_repo, book_read_repo,
):
	"""Two spines resolving to the same not-yet-owned book (e.g. two copies
	standing side by side) must not both be created — this is the case that
	used to reach the DB as two inserts for the same family+ISBN."""
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _confirm_use_case(
		shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo
	)

	result = await use_case.execute(
		ConfirmShelfScanInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			shelf_id=shelf.id,
			items=[
				ConfirmShelfScanItem(title="Dune", main_author="Frank Herbert", isbn="978-0441013593", position=0),
				ConfirmShelfScanItem(title="Dune", main_author="Frank Herbert", isbn="9780441013593", position=1),
			],
		)
	)

	assert len(result.created_book_ids) == 1
	assert result.skipped == [ConfirmShelfScanSkip(title="Dune", reason="duplicate_in_scan", position=1)]


@pytest.mark.asyncio
async def test_confirm_keeps_an_intentional_duplicate_matched_twice_in_one_scan(
	test_family_id, test_user_id, room_repo, bookcase_repo, section_repo, shelf_repo,
	record_repo, book_repo, history_repo, book_read_repo,
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _confirm_use_case(
		shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo
	)

	result = await use_case.execute(
		ConfirmShelfScanInput(
			family_id=test_family_id,
			changed_by=test_user_id,
			shelf_id=shelf.id,
			items=[
				ConfirmShelfScanItem(title="Dune", main_author="Frank Herbert", isbn="9780441013593", position=0),
				ConfirmShelfScanItem(
					title="Dune", main_author="Frank Herbert", isbn="9780441013593", position=1,
					is_intentional_duplicate=True,
				),
			],
		)
	)

	assert len(result.created_book_ids) == 2
	assert result.skipped == []


@pytest.mark.asyncio
async def test_confirm_rejects_a_shelf_of_another_family(
	test_family_id, test_user_id, room_repo, bookcase_repo, section_repo, shelf_repo,
	record_repo, book_repo, history_repo, book_read_repo,
):
	shelf = await _build_shelf(uuid4(), room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _confirm_use_case(
		shelf_repo, section_repo, bookcase_repo, record_repo, book_repo, history_repo, book_read_repo
	)

	with pytest.raises(PermissionError):
		await use_case.execute(
			ConfirmShelfScanInput(
				family_id=test_family_id,
				changed_by=test_user_id,
				shelf_id=shelf.id,
				items=[ConfirmShelfScanItem(title="Dune")],
			)
		)


def _audit_use_case(shelf_repo, section_repo, bookcase_repo, reader, book_repo, record_repo):
	return AuditShelfUseCase(shelf_repo, section_repo, bookcase_repo, reader, book_repo, record_repo)


async def _shelve_book(family_id, shelf_id, title, main_author, record_repo, book_repo):
	record = await record_repo.save(
		BibliographicRecord(family_id=family_id, title=title, main_author=main_author)
	)
	await book_repo.save(
		OwnedBook(family_id=family_id, bibliographic_record_id=record.id, shelf_id=shelf_id)
	)


@pytest.mark.asyncio
async def test_audit_reports_unavailable_when_vision_is_off(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _audit_use_case(
		shelf_repo, section_repo, bookcase_repo, StubSpineReader(None, reason="unsupported"), book_repo, record_repo
	)

	result = await use_case.execute(
		AuditShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
	)

	assert result.available is False
	assert result.reason == "unsupported"


@pytest.mark.asyncio
async def test_audit_classifies_present_missing_and_unexpected(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo)
	await _shelve_book(test_family_id, shelf.id, "Dune", "Frank Herbert", record_repo, book_repo)
	await _shelve_book(test_family_id, shelf.id, "Fondazione", "Isaac Asimov", record_repo, book_repo)

	# Photo shows Dune (present) and Neuromancer (unexpected); Fondazione is gone (missing).
	reader = StubSpineReader([
		SpineReading(title="Dune", author="Frank Herbert", position=0),
		SpineReading(title="Neuromancer", author="William Gibson", position=1),
	])
	use_case = _audit_use_case(shelf_repo, section_repo, bookcase_repo, reader, book_repo, record_repo)

	result = await use_case.execute(
		AuditShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
	)

	assert result.available is True
	assert [b.title for b in result.present] == ["Dune"]
	assert [b.title for b in result.missing] == ["Fondazione"]
	assert [s.title for s in result.unexpected] == ["Neuromancer"]


@pytest.mark.asyncio
async def test_audit_rejects_a_shelf_of_another_family(
	test_family_id, room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo
):
	shelf = await _build_shelf(uuid4(), room_repo, bookcase_repo, section_repo, shelf_repo)
	use_case = _audit_use_case(shelf_repo, section_repo, bookcase_repo, StubSpineReader([]), book_repo, record_repo)

	with pytest.raises(PermissionError):
		await use_case.execute(
			AuditShelfInput(family_id=test_family_id, shelf_id=shelf.id, image_base64="abc", media_type="image/jpeg")
		)
