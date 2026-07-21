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


async def _create_book(client: AsyncClient) -> str:
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
			"title": "Charlotte's Web",
			"main_author": "E. B. White",
			"room_id": room_id,
			"bookcase_id": bookcase_id,
			"section_id": section_id,
			"shelf_id": shelf_id,
			"reading_status": "reading",
		},
	)
	book: str = book_resp.json()["id"]
	return book


async def test_create_journal_entry_requires_kids_mode_enabled(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=False)

	response = await client.post("/v1/kids/journal", json={"owned_book_id": book_id, "text": "I liked it!"})
	assert response.status_code == 403


async def test_child_can_create_and_list_journal_entry(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)

	create = await client.post(
		"/v1/kids/journal",
		json={"owned_book_id": book_id, "text": "Wilbur is my favorite!", "emoji": "🐷", "prompt_kind": "free"},
	)
	assert create.status_code == 201
	body = create.json()
	assert body["owned_book_id"] == book_id
	assert body["user_id"] == str(child_id)
	assert body["text"] == "Wilbur is my favorite!"
	assert body["emoji"] == "🐷"
	assert body["prompt_kind"] == "free"

	listing = await client.get("/v1/kids/journal", params={"user_id": str(child_id)})
	assert listing.status_code == 200
	entries = listing.json()
	assert len(entries) == 1
	assert entries[0]["id"] == body["id"]


async def test_create_journal_entry_requires_text(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)

	response = await client.post("/v1/kids/journal", json={"owned_book_id": book_id, "text": ""})
	assert response.status_code == 422


async def test_create_journal_entry_rejects_book_from_another_library(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	other_library_id = uuid4()
	_override_as(other_library_id, child_id, "child", kids_mode_enabled=True)

	response = await client.post("/v1/kids/journal", json={"owned_book_id": book_id, "text": "Hi"})
	assert response.status_code == 403


async def test_child_cannot_list_another_childs_journal(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()
	other_child_id = uuid4()

	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	await client.post("/v1/kids/journal", json={"owned_book_id": book_id, "text": "Hi"})

	_override_as(library_id, other_child_id, "child", kids_mode_enabled=True)
	response = await client.get("/v1/kids/journal", params={"user_id": str(child_id)})
	assert response.status_code == 403


async def test_parent_can_list_a_childs_journal(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	child_id = uuid4()

	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	await client.post("/v1/kids/journal", json={"owned_book_id": book_id, "text": "Great book"})

	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	response = await client.get("/v1/kids/journal", params={"user_id": str(child_id)})
	assert response.status_code == 200
	assert len(response.json()) == 1


async def test_parent_cannot_write_a_journal_entry(client: AsyncClient, library_id: UUID) -> None:
	"""Unlike KID-02's shared reading sessions, journal entries stay
	self-service only — a parent has no "log on behalf of" path here."""
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)

	response = await client.post("/v1/kids/journal", json={"owned_book_id": book_id, "text": "Hi"})
	assert response.status_code == 403
