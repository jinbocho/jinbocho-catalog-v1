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


async def test_create_reading_path_requires_kids_mode_enabled(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=False)

	response = await client.post("/v1/kids/paths", json={"title": "Adventure starters", "book_ids": [book_id]})
	assert response.status_code == 403


async def test_child_cannot_create_a_reading_path(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	response = await client.post("/v1/kids/paths", json={"title": "Adventure starters", "book_ids": [book_id]})
	assert response.status_code == 403


async def test_parent_can_create_and_list_reading_path(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	create = await client.post(
		"/v1/kids/paths",
		json={
			"title": "Adventure starters",
			"description": "Three books to get hooked on adventure",
			"book_ids": [book_id],
			"target_band": "fluent",
		},
	)
	assert create.status_code == 201
	body = create.json()
	assert body["title"] == "Adventure starters"
	assert body["book_ids"] == [book_id]
	assert body["source"] == "manual"

	listing = await client.get("/v1/kids/paths")
	assert listing.status_code == 200
	paths = listing.json()
	assert len(paths) == 1
	assert paths[0]["id"] == body["id"]


async def test_child_can_list_reading_paths(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	await client.post("/v1/kids/paths", json={"title": "Adventure starters", "book_ids": [book_id]})

	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)
	response = await client.get("/v1/kids/paths")
	assert response.status_code == 200
	assert len(response.json()) == 1


async def test_create_reading_path_requires_at_least_one_book(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	response = await client.post("/v1/kids/paths", json={"title": "Empty path", "book_ids": []})
	assert response.status_code == 422


async def test_parent_can_delete_a_reading_path(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/paths", json={"title": "Adventure starters", "book_ids": [book_id]})
	path_id = created.json()["id"]

	delete = await client.delete(f"/v1/kids/paths/{path_id}")
	assert delete.status_code == 204

	listing = await client.get("/v1/kids/paths")
	assert listing.json() == []


async def test_child_cannot_delete_a_reading_path(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/paths", json={"title": "Adventure starters", "book_ids": [book_id]})
	path_id = created.json()["id"]

	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)
	response = await client.delete(f"/v1/kids/paths/{path_id}")
	assert response.status_code == 403


async def test_delete_reading_path_rejects_path_from_another_library(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/paths", json={"title": "Adventure starters", "book_ids": [book_id]})
	path_id = created.json()["id"]

	other_library_id = uuid4()
	_override_as(other_library_id, uuid4(), "admin", kids_mode_enabled=True)
	response = await client.delete(f"/v1/kids/paths/{path_id}")
	assert response.status_code == 403
