import pytest
from uuid import uuid4, UUID

from app.application.use_cases import (
	CreateRoomInput,
	CreateRoomUseCase,
	GetRoomUseCase,
	ListRoomsUseCase,
	UpdateRoomInput,
	UpdateRoomUseCase,
	DeleteRoomUseCase,
)


@pytest.mark.asyncio
async def test_create_room(room_repo, test_family_id):
	"""Test creating a room."""
	use_case = CreateRoomUseCase(room_repo)
	inp = CreateRoomInput(family_id=test_family_id, name="Living Room", description="Main room")

	room = await use_case.execute(inp)

	assert room.name == "Living Room"
	assert room.description == "Main room"
	assert room.family_id == test_family_id


@pytest.mark.asyncio
async def test_get_room(room_repo, test_family_id):
	"""Test retrieving a room."""
	use_case = CreateRoomUseCase(room_repo)
	inp = CreateRoomInput(family_id=test_family_id, name="Bedroom", description="Sleeping room")

	room = await use_case.execute(inp)

	get_use_case = GetRoomUseCase(room_repo)
	retrieved = await get_use_case.execute(room.id, test_family_id)

	assert retrieved.id == room.id
	assert retrieved.name == "Bedroom"


@pytest.mark.asyncio
async def test_get_room_not_found(room_repo, test_family_id):
	"""Test getting a non-existent room."""
	use_case = GetRoomUseCase(room_repo)

	with pytest.raises(LookupError):
		await use_case.execute(uuid4(), test_family_id)


@pytest.mark.asyncio
async def test_get_room_wrong_family(room_repo, test_family_id):
	"""Test accessing a room from wrong family."""
	create_use_case = CreateRoomUseCase(room_repo)
	inp = CreateRoomInput(family_id=test_family_id, name="Room1", description=None)
	room = await create_use_case.execute(inp)

	get_use_case = GetRoomUseCase(room_repo)
	other_family_id = uuid4()

	with pytest.raises(PermissionError):
		await get_use_case.execute(room.id, other_family_id)


@pytest.mark.asyncio
async def test_update_room(room_repo, test_family_id):
	"""Test updating a room."""
	create_use_case = CreateRoomUseCase(room_repo)
	inp = CreateRoomInput(family_id=test_family_id, name="Old Name", description="Old")
	room = await create_use_case.execute(inp)

	update_use_case = UpdateRoomUseCase(room_repo)
	update_inp = UpdateRoomInput(room_id=room.id, family_id=test_family_id, name="New Name", description="Updated")
	updated = await update_use_case.execute(update_inp)

	assert updated.name == "New Name"
	assert updated.description == "Updated"


@pytest.mark.asyncio
async def test_list_rooms(room_repo, test_family_id):
	"""Test listing rooms."""
	create_use_case = CreateRoomUseCase(room_repo)

	# Create 3 rooms
	for i in range(3):
		inp = CreateRoomInput(family_id=test_family_id, name=f"Room {i}", description=None)
		await create_use_case.execute(inp)

	list_use_case = ListRoomsUseCase(room_repo)
	rooms = await list_use_case.execute(test_family_id, limit=50, offset=0)

	assert len(rooms) == 3


@pytest.mark.asyncio
async def test_delete_room(room_repo, test_family_id):
	"""Test deleting a room."""
	create_use_case = CreateRoomUseCase(room_repo)
	inp = CreateRoomInput(family_id=test_family_id, name="ToDelete", description=None)
	room = await create_use_case.execute(inp)

	delete_use_case = DeleteRoomUseCase(room_repo)
	await delete_use_case.execute(room.id, test_family_id)

	# Verify it's deleted
	get_use_case = GetRoomUseCase(room_repo)
	with pytest.raises(LookupError):
		await get_use_case.execute(room.id, test_family_id)
