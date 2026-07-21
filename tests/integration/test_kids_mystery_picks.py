from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient

from app.api.dependencies import get_current_user_payload
from app.main import app


def _payload(library_id: UUID, user_id: UUID, role: str, kids_mode_enabled: bool) -> dict[str, Any]:
	return {
		"library_id": str(library_id),
		"sub": str(user_id),
		"role": role,
		"kids_mode_enabled": kids_mode_enabled,
	}


def _override_as(library_id: UUID, user_id: UUID, role: str, kids_mode_enabled: bool) -> None:
	async def _override() -> dict[str, Any]:
		return _payload(library_id, user_id, role, kids_mode_enabled)

	app.dependency_overrides[get_current_user_payload] = _override


async def _create_book(client: AsyncClient, title: str = "Charlotte's Web") -> str:
	room_resp = await client.post("/v1/rooms/", json={"name": "Kids room"})
	room_id = room_resp.json()["id"]
	bookcase_resp = await client.post("/v1/bookcases/", json={"room_id": room_id, "name": "Shelf A"})
	bookcase_id = bookcase_resp.json()["id"]
	section_resp = await client.post("/v1/sections/", json={"bookcase_id": bookcase_id, "section_index": 0})
	section_id = section_resp.json()["id"]
	shelf_resp = await client.post("/v1/shelves/", json={"section_id": section_id, "shelf_index": 0})
	shelf_id = shelf_resp.json()["id"]
	book_resp = await client.post(
		"/v1/books/",
		json={
			"title": title,
			"main_author": "E. B. White",
			"room_id": room_id,
			"bookcase_id": bookcase_id,
			"section_id": section_id,
			"shelf_id": shelf_id,
			"reading_status": "to_read",
		},
	)
	book: str = book_resp.json()["id"]
	return book


async def test_create_mystery_pick_requires_kids_mode_enabled(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=False)

	response = await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(uuid4())})
	assert response.status_code == 403


async def test_child_cannot_create_a_mystery_pick(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	response = await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(uuid4())})
	assert response.status_code == 403


async def test_parent_creates_pick_and_sees_the_book_immediately(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	response = await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(child_id)})
	assert response.status_code == 201
	body = response.json()
	assert body["owned_book_id"] == book_id
	assert body["status"] == "proposed"
	assert body["hint_text"]
	assert "Charlotte's Web" not in body["hint_text"]


async def test_child_does_not_see_the_book_until_accepted(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(child_id)})

	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	listing = await client.get("/v1/kids/mystery", params={"child_user_id": str(child_id)})
	assert listing.status_code == 200
	picks = listing.json()
	assert len(picks) == 1
	assert picks[0]["owned_book_id"] is None
	assert picks[0]["status"] == "proposed"


async def test_child_can_accept_and_then_sees_the_book(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(child_id)})
	pick_id = created.json()["id"]

	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	accept = await client.post(f"/v1/kids/mystery/{pick_id}/accept")
	assert accept.status_code == 200
	body = accept.json()
	assert body["status"] == "accepted"
	assert body["owned_book_id"] == book_id

	listing = await client.get("/v1/kids/mystery", params={"child_user_id": str(child_id)})
	assert listing.json()[0]["owned_book_id"] == book_id


async def test_another_child_cannot_accept_someone_elses_pick(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	other_child_id = uuid4()
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(child_id)})
	pick_id = created.json()["id"]

	_override_as(library_id, other_child_id, "child", kids_mode_enabled=True)
	response = await client.post(f"/v1/kids/mystery/{pick_id}/accept")
	assert response.status_code == 403


async def test_child_cannot_list_another_childs_picks(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	other_child_id = uuid4()
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(child_id)})

	_override_as(library_id, other_child_id, "child", kids_mode_enabled=True)
	response = await client.get("/v1/kids/mystery", params={"child_user_id": str(child_id)})
	assert response.status_code == 403


async def test_parent_always_sees_the_book_even_while_proposed(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	await client.post("/v1/kids/mystery", json={"owned_book_id": book_id, "child_user_id": str(child_id)})

	listing = await client.get("/v1/kids/mystery", params={"child_user_id": str(child_id)})
	assert listing.json()[0]["owned_book_id"] == book_id
