from uuid import uuid4

import pytest

from app.application.use_cases import DeleteLibraryDataUseCase, RecordRemovedMemberInput, RecordRemovedMemberUseCase
from app.domain.entities import BibliographicRecord, Bookcase, BookEventType, BookHistory, LibraryRole, OwnedBook, Room


def _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo):
	return DeleteLibraryDataUseCase(
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		record_repo=record_repo,
		book_repo=book_repo,
		book_history_repo=history_repo,
		removed_member_repo=removed_member_repo,
	)


@pytest.mark.asyncio
async def test_delete_library_data_wipes_everything_for_the_library(
	room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo, test_library_id,
):
	room = await room_repo.save(Room(library_id=test_library_id, name="Living room"))
	bookcase = await bookcase_repo.save(Bookcase(library_id=test_library_id, room_id=room.id, name="Shelf A"))
	record = await record_repo.save(BibliographicRecord(library_id=test_library_id, title="Dune"))
	book = await book_repo.save(
		OwnedBook(library_id=test_library_id, bibliographic_record_id=record.id, bookcase_id=bookcase.id)
	)
	await history_repo.save(
		BookHistory(id=uuid4(), owned_book_id=book.id, event_type=BookEventType.CREATED, changed_by=uuid4())
	)
	await RecordRemovedMemberUseCase(removed_member_repo).execute(
		RecordRemovedMemberInput(
			library_id=test_library_id, id=uuid4(), full_name="Gone", email="gone@example.com", role=LibraryRole.VIEWER
		)
	)

	use_case = _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo)
	result = await use_case.execute(test_library_id)

	assert result.rooms_deleted == 1
	assert result.bookcases_deleted == 1
	assert result.records_deleted == 1
	assert result.owned_books_deleted == 1
	assert result.removed_members_deleted == 1

	assert await room_repo.find_all_by_library(test_library_id) == []
	assert await bookcase_repo.find_all_by_library(test_library_id) == []
	assert await record_repo.find_all_by_library(test_library_id) == []
	assert await book_repo.find_all_by_library(test_library_id) == []
	assert await history_repo.find_by_book(book.id) == []
	assert await removed_member_repo.find_all_by_library(test_library_id) == []


@pytest.mark.asyncio
async def test_delete_library_data_does_not_touch_another_library(
	room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo, test_library_id,
):
	other_library_id = uuid4()
	await room_repo.save(Room(library_id=test_library_id, name="Mine"))
	other_room = await room_repo.save(Room(library_id=other_library_id, name="Not mine"))

	use_case = _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo)
	await use_case.execute(test_library_id)

	remaining = await room_repo.find_all_by_library(other_library_id)
	assert [r.id for r in remaining] == [other_room.id]


@pytest.mark.asyncio
async def test_delete_library_data_on_an_empty_library_is_a_safe_no_op(
	room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo, test_library_id,
):
	use_case = _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo)
	result = await use_case.execute(test_library_id)

	assert result.rooms_deleted == 0
	assert result.owned_books_deleted == 0
