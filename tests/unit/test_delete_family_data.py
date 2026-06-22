from uuid import uuid4

import pytest

from app.application.use_cases import DeleteFamilyDataUseCase, RecordRemovedMemberInput, RecordRemovedMemberUseCase
from app.domain.entities import BibliographicRecord, Bookcase, BookEventType, BookHistory, FamilyRole, OwnedBook, Room


def _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo):
	return DeleteFamilyDataUseCase(
		room_repo=room_repo,
		bookcase_repo=bookcase_repo,
		record_repo=record_repo,
		book_repo=book_repo,
		book_history_repo=history_repo,
		removed_member_repo=removed_member_repo,
	)


@pytest.mark.asyncio
async def test_delete_family_data_wipes_everything_for_the_family(
	room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo, test_family_id,
):
	room = await room_repo.save(Room(family_id=test_family_id, name="Living room"))
	bookcase = await bookcase_repo.save(Bookcase(family_id=test_family_id, room_id=room.id, name="Shelf A"))
	record = await record_repo.save(BibliographicRecord(family_id=test_family_id, title="Dune"))
	book = await book_repo.save(
		OwnedBook(family_id=test_family_id, bibliographic_record_id=record.id, bookcase_id=bookcase.id)
	)
	await history_repo.save(
		BookHistory(id=uuid4(), owned_book_id=book.id, event_type=BookEventType.CREATED, changed_by=uuid4())
	)
	await RecordRemovedMemberUseCase(removed_member_repo).execute(
		RecordRemovedMemberInput(
			family_id=test_family_id, id=uuid4(), full_name="Gone", email="gone@example.com", role=FamilyRole.VIEWER
		)
	)

	use_case = _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo)
	result = await use_case.execute(test_family_id)

	assert result.rooms_deleted == 1
	assert result.bookcases_deleted == 1
	assert result.records_deleted == 1
	assert result.owned_books_deleted == 1
	assert result.removed_members_deleted == 1

	assert await room_repo.find_all_by_family(test_family_id) == []
	assert await bookcase_repo.find_all_by_family(test_family_id) == []
	assert await record_repo.find_all_by_family(test_family_id) == []
	assert await book_repo.find_all_by_family(test_family_id) == []
	assert await history_repo.find_by_book(book.id) == []
	assert await removed_member_repo.find_all_by_family(test_family_id) == []


@pytest.mark.asyncio
async def test_delete_family_data_does_not_touch_another_family(
	room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo, test_family_id,
):
	other_family_id = uuid4()
	await room_repo.save(Room(family_id=test_family_id, name="Mine"))
	other_room = await room_repo.save(Room(family_id=other_family_id, name="Not mine"))

	use_case = _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo)
	await use_case.execute(test_family_id)

	remaining = await room_repo.find_all_by_family(other_family_id)
	assert [r.id for r in remaining] == [other_room.id]


@pytest.mark.asyncio
async def test_delete_family_data_on_an_empty_family_is_a_safe_no_op(
	room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo, test_family_id,
):
	use_case = _use_case(room_repo, bookcase_repo, record_repo, book_repo, history_repo, removed_member_repo)
	result = await use_case.execute(test_family_id)

	assert result.rooms_deleted == 0
	assert result.owned_books_deleted == 0
