from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.application.use_cases import (
	ExportFullLibraryUseCase,
	ImportBookcaseItem,
	ImportBookHistoryItem,
	ImportBookLoanItem,
	ImportFullLibraryInput,
	ImportFullLibraryUseCase,
	ImportOwnedBookItem,
	ImportRecordItem,
	ImportRoomItem,
	ImportSectionItem,
	ImportShelfItem,
	RecordRemovedMemberInput,
	RecordRemovedMemberUseCase,
)
from app.domain.entities import BibliographicRecord, BookLoan, FamilyRole, OwnedBook, Room


def _export_use_case(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, removed_member_repo, wishlist_repo,
):
	return ExportFullLibraryUseCase(
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		section_repo=section_repo,
		shelf_repo=shelf_repo,
		record_repo=record_repo,
		book_repo=book_repo,
		book_read_repo=book_read_repo,
		book_loan_repo=book_loan_repo,
		book_history_repo=history_repo,
		removed_member_repo=removed_member_repo,
		wishlist_repo=wishlist_repo,
	)


def _import_use_case(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, wishlist_repo,
):
	return ImportFullLibraryUseCase(
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		section_repo=section_repo,
		shelf_repo=shelf_repo,
		record_repo=record_repo,
		book_repo=book_repo,
		book_read_repo=book_read_repo,
		book_loan_repo=book_loan_repo,
		book_history_repo=history_repo,
		wishlist_repo=wishlist_repo,
	)


@pytest.mark.asyncio
async def test_export_full_library_includes_empty_locations_and_all_loans(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, removed_member_repo, wishlist_repo, test_family_id,
):
	# An empty room with no books — the books-only export drops this entirely.
	await room_repo.save(Room(family_id=test_family_id, name="Empty attic"))

	record = await record_repo.save(BibliographicRecord(family_id=test_family_id, title="Dune"))
	book = await book_repo.save(OwnedBook(family_id=test_family_id, bibliographic_record_id=record.id))

	# A returned loan — list_active_by_family would drop this, find_all_by_family must not.
	await book_loan_repo.add(BookLoan(owned_book_id=book.id, borrower_name="Alice"))
	returned_loan = await book_loan_repo.add(BookLoan(owned_book_id=book.id, borrower_name="Bob"))
	await book_loan_repo.mark_returned(returned_loan.id, datetime.now(UTC))

	use_case = _export_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, removed_member_repo, wishlist_repo,
	)
	result = await use_case.execute(test_family_id)

	assert len(result.rooms) == 1
	assert result.rooms[0].name == "Empty attic"
	assert len(result.owned_books) == 1
	assert len(result.book_loans) == 2  # both active and returned


@pytest.mark.asyncio
async def test_export_full_library_pagination_loop_fetches_everything(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, removed_member_repo, wishlist_repo, test_family_id, monkeypatch,
):
	"""Regression: the books-only export silently caps at the FE's default page
	size. Shrink the internal page size so a handful of rooms already exercises
	more than one page, and confirm every room still comes back."""
	import app.application.services.pagination as pagination_module
	monkeypatch.setattr(pagination_module, "DEFAULT_PAGE_SIZE", 2)

	for i in range(5):
		await room_repo.save(Room(family_id=test_family_id, name=f"Room {i}"))

	use_case = _export_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, removed_member_repo, wishlist_repo,
	)
	result = await use_case.execute(test_family_id)

	assert len(result.rooms) == 5


@pytest.mark.asyncio
async def test_record_removed_member_snapshot_is_included_in_export(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, removed_member_repo, wishlist_repo, test_family_id,
):
	"""A member removed from auth-service must show up in the full-library
	export, so a future import can recreate their real account by email
	instead of leaving owner_id/etc. references unresolved."""
	removed_id = uuid4()
	await RecordRemovedMemberUseCase(removed_member_repo).execute(
		RecordRemovedMemberInput(
			family_id=test_family_id, id=removed_id, full_name="Giuseppe Bianchi", email="giuseppe@example.com",
			role=FamilyRole.VIEWER,
		)
	)

	use_case = _export_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, removed_member_repo, wishlist_repo,
	)
	result = await use_case.execute(test_family_id)

	assert len(result.removed_members) == 1
	snapshot = result.removed_members[0]
	assert snapshot.id == removed_id
	assert snapshot.full_name == "Giuseppe Bianchi"
	assert snapshot.email == "giuseppe@example.com"
	assert snapshot.role is FamilyRole.VIEWER


@pytest.mark.asyncio
async def test_record_removed_member_upserts_by_id(removed_member_repo, test_family_id):
	"""Recording the same removal twice (e.g. a retried request) must
	overwrite the snapshot, not create a duplicate."""
	removed_id = uuid4()
	use_case = RecordRemovedMemberUseCase(removed_member_repo)
	await use_case.execute(
		RecordRemovedMemberInput(
			family_id=test_family_id, id=removed_id, full_name="Old Name",
			email="old@example.com", role=FamilyRole.VIEWER,
		)
	)
	await use_case.execute(
		RecordRemovedMemberInput(
			family_id=test_family_id, id=removed_id, full_name="New Name",
			email="new@example.com", role=FamilyRole.EDITOR,
		)
	)

	all_for_family = await removed_member_repo.find_all_by_family(test_family_id)
	assert len(all_for_family) == 1
	assert all_for_family[0].full_name == "New Name"
	assert all_for_family[0].email == "new@example.com"


@pytest.mark.asyncio
async def test_import_full_library_into_empty_family_resolves_relationships(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, wishlist_repo, test_family_id, test_user_id,
):
	room_id, bookcase_id, section_id, shelf_id, record_id, book_id = (uuid4() for _ in range(6))

	use_case = _import_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, wishlist_repo,
	)
	result = await use_case.execute(
		ImportFullLibraryInput(
			family_id=test_family_id,
			user_id_map={test_user_id: test_user_id},
			rooms=[ImportRoomItem(id=room_id, name="Living room")],
			bookcases=[ImportBookcaseItem(id=bookcase_id, room_id=room_id, name="Big shelf")],
			sections=[ImportSectionItem(id=section_id, bookcase_id=bookcase_id, section_index=0)],
			shelves=[ImportShelfItem(id=shelf_id, section_id=section_id, shelf_index=0)],
			bibliographic_records=[ImportRecordItem(id=record_id, title="Dune", isbn="9780441013593")],
			owned_books=[
				ImportOwnedBookItem(
					id=book_id, bibliographic_record_id=record_id, room_id=room_id, bookcase_id=bookcase_id,
					section_id=section_id, shelf_id=shelf_id, owner_id=test_user_id,
				)
			],
		)
	)

	assert result.rooms_imported == 1
	assert result.owned_books_imported == 1
	assert result.records_imported == 1
	assert result.records_deduped == 0

	# Every id is regenerated on import (see ImportFullLibraryUseCase docstring
	# for why preserving the original id is unsafe) — but relationships must
	# still resolve correctly through the new ids.
	imported_books = await book_repo.find_all_by_family(test_family_id)
	assert len(imported_books) == 1
	imported_book = imported_books[0]
	assert imported_book.id != book_id
	assert imported_book.family_id == test_family_id
	assert imported_book.owner_id == test_user_id

	imported_room = await room_repo.find_by_id(imported_book.room_id)
	assert imported_room is not None
	assert imported_room.id != room_id
	assert imported_room.name == "Living room"

	imported_record = await record_repo.find_by_id(imported_book.bibliographic_record_id)
	assert imported_record.id != record_id
	assert imported_record.title == "Dune"


@pytest.mark.asyncio
async def test_import_full_library_does_not_clobber_an_existing_row_sharing_the_export_id(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, wishlist_repo, test_family_id,
):
	"""Regression: a previous version of this use case preserved the
	exported id and upserted by it. If that same id already existed —
	belonging to a *different* family, e.g. the one the backup was originally
	exported from, still live in the same database — the import silently
	landed on and overwrote that unrelated row instead of creating a new one
	for the importing family."""
	other_family_id = uuid4()
	shared_id = uuid4()
	original_room = await room_repo.save(
		Room(id=shared_id, family_id=other_family_id, name="Original family's room")
	)

	use_case = _import_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, wishlist_repo,
	)
	await use_case.execute(
		ImportFullLibraryInput(
			family_id=test_family_id,
			rooms=[ImportRoomItem(id=shared_id, name="Imported room")],
		)
	)

	# The original family's room must be untouched.
	untouched = await room_repo.find_by_id(original_room.id)
	assert untouched.family_id == other_family_id
	assert untouched.name == "Original family's room"

	# The importing family must have gotten its own, separate room.
	new_rooms = await room_repo.find_all_by_family(test_family_id)
	assert len(new_rooms) == 1
	assert new_rooms[0].name == "Imported room"
	assert new_rooms[0].id != shared_id


@pytest.mark.asyncio
async def test_import_full_library_dedupes_record_by_isbn_on_merge(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, wishlist_repo, test_family_id,
):
	"""Merge case: the family already owns this ISBN — re-importing it must
	reuse the existing record rather than violate the (family_id, isbn) unique
	constraint or create a visible duplicate."""
	existing_record = await record_repo.save(
		BibliographicRecord(family_id=test_family_id, title="Dune (existing copy)", isbn="9780441013593")
	)

	incoming_record_id = uuid4()
	book_id = uuid4()
	use_case = _import_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, wishlist_repo,
	)
	result = await use_case.execute(
		ImportFullLibraryInput(
			family_id=test_family_id,
			bibliographic_records=[
				ImportRecordItem(id=incoming_record_id, title="Dune (imported copy)", isbn="9780441013593")
			],
			owned_books=[ImportOwnedBookItem(id=book_id, bibliographic_record_id=incoming_record_id)],
		)
	)

	assert result.records_deduped == 1
	assert result.records_imported == 0

	imported_books = await book_repo.find_all_by_family(test_family_id)
	assert len(imported_books) == 1
	# The book must point at the *existing* record, not a freshly inserted duplicate.
	assert imported_books[0].bibliographic_record_id == existing_record.id
	kept_record = await record_repo.find_by_id(existing_record.id)
	assert kept_record.title == "Dune (existing copy)"  # existing data wins, not overwritten


@pytest.mark.asyncio
async def test_import_full_library_twice_does_not_duplicate_anything(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, wishlist_repo, test_family_id, test_user_id,
):
	"""The exact scenario the user asked for: importing the same backup a
	second time (or merging an overlapping one) must not pile up duplicate
	rooms, bookcases, sections, shelves, or books — every entity dedupes by
	its natural key, not just bibliographic records by ISBN."""
	room_id, bookcase_id, section_id, shelf_id, record_id, book_id = (uuid4() for _ in range(6))

	def build_payload():
		return ImportFullLibraryInput(
			family_id=test_family_id,
			user_id_map={test_user_id: test_user_id},
			rooms=[ImportRoomItem(id=room_id, name="Living room")],
			bookcases=[ImportBookcaseItem(id=bookcase_id, room_id=room_id, name="Big shelf")],
			sections=[ImportSectionItem(id=section_id, bookcase_id=bookcase_id, section_index=0)],
			shelves=[ImportShelfItem(id=shelf_id, section_id=section_id, shelf_index=0)],
			bibliographic_records=[ImportRecordItem(id=record_id, title="Dune", isbn="9780441013593")],
			owned_books=[
				ImportOwnedBookItem(
					id=book_id, bibliographic_record_id=record_id, room_id=room_id, bookcase_id=bookcase_id,
					section_id=section_id, shelf_id=shelf_id, owner_id=test_user_id,
				)
			],
			book_loans=[
				ImportBookLoanItem(
					id=uuid4(), owned_book_id=book_id, borrower_name="Alice",
					loaned_at=datetime(2026, 1, 1, tzinfo=UTC),
				)
			],
			book_history=[
				ImportBookHistoryItem(
					id=uuid4(), owned_book_id=book_id, event_type="created", changed_by=test_user_id,
					created_at=datetime(2026, 1, 1, tzinfo=UTC),
				)
			],
		)

	use_case = _import_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, wishlist_repo,
	)
	first = await use_case.execute(build_payload())
	assert first.rooms_imported == 1
	assert first.owned_books_imported == 1

	second = await use_case.execute(build_payload())

	# Nothing new was created the second time around.
	assert second.rooms_imported == 0
	assert second.rooms_deduped == 1
	assert second.bookcases_imported == 0
	assert second.bookcases_deduped == 1
	assert second.sections_imported == 0
	assert second.sections_deduped == 1
	assert second.shelves_imported == 0
	assert second.shelves_deduped == 1
	assert second.records_imported == 0
	assert second.records_deduped == 1
	assert second.owned_books_imported == 0
	assert second.owned_books_deduped == 1

	# The family's actual data has exactly one of everything, not two.
	assert len(await room_repo.find_all_by_family(test_family_id)) == 1
	assert len(await book_repo.find_all_by_family(test_family_id)) == 1
	assert len(await record_repo.find_all_by_family(test_family_id)) == 1
	imported_book = (await book_repo.find_all_by_family(test_family_id))[0]
	assert len(await history_repo.find_all_by_family(test_family_id)) == 1
	assert len(await book_loan_repo.find_all_by_family(test_family_id)) == 1
	assert imported_book.owner_id == test_user_id


@pytest.mark.asyncio
async def test_import_full_library_rewrites_user_ids_via_map(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, wishlist_repo, test_family_id,
):
	old_owner_id = uuid4()
	new_owner_id = uuid4()
	record_id, book_id = uuid4(), uuid4()

	use_case = _import_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, wishlist_repo,
	)
	await use_case.execute(
		ImportFullLibraryInput(
			family_id=test_family_id,
			user_id_map={old_owner_id: new_owner_id},
			bibliographic_records=[ImportRecordItem(id=record_id, title="Dune")],
			owned_books=[ImportOwnedBookItem(id=book_id, bibliographic_record_id=record_id, owner_id=old_owner_id)],
		)
	)

	imported_books = await book_repo.find_all_by_family(test_family_id)
	assert len(imported_books) == 1
	assert imported_books[0].owner_id == new_owner_id


@pytest.mark.asyncio
async def test_import_full_library_rejects_structurally_broken_payload(
	room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
	book_loan_repo, history_repo, wishlist_repo, test_family_id,
):
	use_case = _import_use_case(
		room_repo, bookcase_repo, section_repo, shelf_repo, record_repo, book_repo, book_read_repo,
		book_loan_repo, history_repo, wishlist_repo,
	)
	with pytest.raises(ValueError):
		await use_case.execute(
			ImportFullLibraryInput(
				family_id=test_family_id,
				owned_books=[ImportOwnedBookItem(id=uuid4(), bibliographic_record_id=uuid4())],  # record not in payload
			)
		)

	# Nothing should have been written before the rejection.
	assert (await book_repo.find_all_by_family(test_family_id)) == []
