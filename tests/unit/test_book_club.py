from uuid import uuid4

import pytest

from app.application.use_cases import (
	AddPostInput,
	AddPostUseCase,
	AdvanceCycleStatusInput,
	AdvanceCycleStatusUseCase,
	ArchiveCycleUseCase,
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	CreateCycleInput,
	CreateCycleUseCase,
	DeletePostUseCase,
	GetCycleUseCase,
	ListCyclesUseCase,
	ListPostsUseCase,
)
from app.domain.entities.book_club_cycle import BookClubCycleStatus


async def _make_record(record_repo, library_id, title="Dune"):
	return await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=library_id, title=title)
	)


async def _make_cycle(cycle_repo, record_repo, book_repo, library_id, user_id):
	record = await _make_record(record_repo, library_id)
	return await CreateCycleUseCase(cycle_repo, record_repo, book_repo).execute(
		CreateCycleInput(
			library_id=library_id,
			created_by=user_id,
			bibliographic_record_id=record.id,
			title="Summer reads",
		)
	)


async def _discussing_cycle(cycle_repo, record_repo, book_repo, library_id, user_id):
	"""Discussion only opens once a cycle is advanced past reading — most post
	tests need a cycle already in that state."""
	cycle = await _make_cycle(cycle_repo, record_repo, book_repo, library_id, user_id)
	return await AdvanceCycleStatusUseCase(cycle_repo).execute(
		AdvanceCycleStatusInput(
			cycle_id=cycle.id, library_id=library_id, target_status=BookClubCycleStatus.DISCUSSING
		)
	)


@pytest.mark.asyncio
async def test_create_cycle_starts_in_reading(cycle_repo, record_repo, book_repo, test_library_id, test_user_id):
	cycle = await _make_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	assert cycle.status is BookClubCycleStatus.READING
	assert cycle.created_by == test_user_id


@pytest.mark.asyncio
async def test_create_cycle_rejects_record_from_other_library(
	cycle_repo, record_repo, book_repo, test_library_id, test_user_id
):
	record = await _make_record(record_repo, uuid4())

	with pytest.raises(PermissionError):
		await CreateCycleUseCase(cycle_repo, record_repo, book_repo).execute(
			CreateCycleInput(
				library_id=test_library_id,
				created_by=test_user_id,
				bibliographic_record_id=record.id,
				title="x",
			)
		)


@pytest.mark.asyncio
async def test_create_cycle_missing_record_raises(cycle_repo, record_repo, book_repo, test_library_id, test_user_id):
	with pytest.raises(LookupError):
		await CreateCycleUseCase(cycle_repo, record_repo, book_repo).execute(
			CreateCycleInput(
				library_id=test_library_id,
				created_by=test_user_id,
				bibliographic_record_id=uuid4(),
				title="x",
			)
		)


@pytest.mark.asyncio
async def test_advance_status_reading_to_discussing(
	cycle_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _make_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	advanced = await AdvanceCycleStatusUseCase(cycle_repo).execute(
		AdvanceCycleStatusInput(
			cycle_id=cycle.id,
			library_id=test_library_id,
			target_status=BookClubCycleStatus.DISCUSSING,
		)
	)

	assert advanced.status is BookClubCycleStatus.DISCUSSING


@pytest.mark.asyncio
async def test_advance_status_illegal_transition_raises(
	cycle_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _make_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	with pytest.raises(ValueError):
		await AdvanceCycleStatusUseCase(cycle_repo).execute(
			AdvanceCycleStatusInput(
				cycle_id=cycle.id,
				library_id=test_library_id,
				target_status=BookClubCycleStatus.ARCHIVED,
			)
		)


@pytest.mark.asyncio
async def test_get_and_list_cycles_scoped_to_library(
	cycle_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _make_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	fetched = await GetCycleUseCase(cycle_repo).execute(cycle.id, test_library_id)
	assert fetched.id == cycle.id

	with pytest.raises(PermissionError):
		await GetCycleUseCase(cycle_repo).execute(cycle.id, uuid4())

	listed = await ListCyclesUseCase(cycle_repo).execute(test_library_id)
	assert [c.id for c in listed] == [cycle.id]
	assert await ListCyclesUseCase(cycle_repo).execute(uuid4()) == []


@pytest.mark.asyncio
async def test_archive_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id):
	cycle = await _discussing_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	archived = await ArchiveCycleUseCase(cycle_repo).execute(cycle.id, test_library_id)

	assert archived.status is BookClubCycleStatus.ARCHIVED


@pytest.mark.asyncio
async def test_archive_from_reading_raises(cycle_repo, record_repo, book_repo, test_library_id, test_user_id):
	# A cycle must pass through discussion before it can be closed.
	cycle = await _make_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	with pytest.raises(ValueError):
		await ArchiveCycleUseCase(cycle_repo).execute(cycle.id, test_library_id)


@pytest.mark.asyncio
async def test_undo_move_to_discussion(cycle_repo, record_repo, book_repo, test_library_id, test_user_id):
	cycle = await _discussing_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	reverted = await AdvanceCycleStatusUseCase(cycle_repo).execute(
		AdvanceCycleStatusInput(
			cycle_id=cycle.id, library_id=test_library_id, target_status=BookClubCycleStatus.READING
		)
	)

	assert reverted.status is BookClubCycleStatus.READING


@pytest.mark.asyncio
async def test_reopen_archived_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id):
	cycle = await _discussing_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	await ArchiveCycleUseCase(cycle_repo).execute(cycle.id, test_library_id)

	reopened = await AdvanceCycleStatusUseCase(cycle_repo).execute(
		AdvanceCycleStatusInput(
			cycle_id=cycle.id, library_id=test_library_id, target_status=BookClubCycleStatus.DISCUSSING
		)
	)

	assert reopened.status is BookClubCycleStatus.DISCUSSING


@pytest.mark.asyncio
async def test_add_and_list_posts(cycle_repo, post_repo, record_repo, book_repo, test_library_id, test_user_id):
	cycle = await _discussing_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)

	post = await AddPostUseCase(cycle_repo, post_repo).execute(
		AddPostInput(
			cycle_id=cycle.id,
			library_id=test_library_id,
			user_id=test_user_id,
			body="Loved the ending",
		)
	)

	posts = await ListPostsUseCase(cycle_repo, post_repo).execute(cycle.id, test_library_id)
	assert [p.id for p in posts] == [post.id]


@pytest.mark.asyncio
async def test_add_post_blocked_outside_discussing(
	cycle_repo, post_repo, record_repo, book_repo, test_library_id, test_user_id
):
	# Discussion only opens once "Move to discussion" was clicked — before
	# that (still reading) or after undoing/archiving, posting is disabled.
	cycle = await _make_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	assert cycle.status is BookClubCycleStatus.READING

	with pytest.raises(PermissionError):
		await AddPostUseCase(cycle_repo, post_repo).execute(
			AddPostInput(cycle_id=cycle.id, library_id=test_library_id, user_id=test_user_id, body="too early")
		)


@pytest.mark.asyncio
async def test_add_reply_to_wrong_cycle_raises(
	cycle_repo, post_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle_a = await _discussing_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	cycle_b = await _discussing_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	parent = await AddPostUseCase(cycle_repo, post_repo).execute(
		AddPostInput(cycle_id=cycle_a.id, library_id=test_library_id, user_id=test_user_id, body="root")
	)

	with pytest.raises(ValueError):
		await AddPostUseCase(cycle_repo, post_repo).execute(
			AddPostInput(
				cycle_id=cycle_b.id,
				library_id=test_library_id,
				user_id=test_user_id,
				body="reply",
				parent_post_id=parent.id,
			)
		)


@pytest.mark.asyncio
async def test_delete_post_author_only_unless_admin(
	cycle_repo, post_repo, record_repo, book_repo, test_library_id, test_user_id
):
	cycle = await _discussing_cycle(cycle_repo, record_repo, book_repo, test_library_id, test_user_id)
	post = await AddPostUseCase(cycle_repo, post_repo).execute(
		AddPostInput(cycle_id=cycle.id, library_id=test_library_id, user_id=test_user_id, body="mine")
	)

	other_user = uuid4()
	with pytest.raises(PermissionError):
		await DeletePostUseCase(cycle_repo, post_repo).execute(
			post_id=post.id, library_id=test_library_id, user_id=other_user, is_admin=False
		)

	await DeletePostUseCase(cycle_repo, post_repo).execute(
		post_id=post.id, library_id=test_library_id, user_id=other_user, is_admin=True
	)
	assert await post_repo.find_by_id(post.id) is None
