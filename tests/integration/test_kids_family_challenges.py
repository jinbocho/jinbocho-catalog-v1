from datetime import date, timedelta
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
			"reading_status": "to_read",
		},
	)
	book: str = book_resp.json()["id"]
	return book


def _challenge_body(metric: str = "minutes", target: int = 100) -> dict[str, Any]:
	today = date.today()
	return {
		"title": "Summer reading marathon",
		"metric": metric,
		"target": target,
		"starts_on": (today - timedelta(days=1)).isoformat(),
		"ends_on": (today + timedelta(days=30)).isoformat(),
	}


async def test_create_challenge_requires_kids_mode_enabled(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=False)

	response = await client.post("/v1/kids/challenges", json=_challenge_body())
	assert response.status_code == 403


async def test_child_cannot_create_a_challenge(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	response = await client.post("/v1/kids/challenges", json=_challenge_body())
	assert response.status_code == 403


async def test_parent_can_create_and_list_challenge(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	create = await client.post("/v1/kids/challenges", json=_challenge_body())
	assert create.status_code == 201
	body = create.json()
	assert body["title"] == "Summer reading marathon"
	assert body["metric"] == "minutes"
	assert body["target"] == 100

	listing = await client.get("/v1/kids/challenges")
	assert listing.status_code == 200
	assert len(listing.json()) == 1


async def test_child_can_list_challenges(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	await client.post("/v1/kids/challenges", json=_challenge_body())

	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)
	response = await client.get("/v1/kids/challenges")
	assert response.status_code == 200
	assert len(response.json()) == 1


async def test_progress_sums_minutes_across_every_member(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/challenges", json=_challenge_body(metric="minutes", target=100))
	challenge_id = created.json()["id"]

	child_a = uuid4()
	child_b = uuid4()
	_override_as(library_id, child_a, "child", kids_mode_enabled=True)
	await client.post("/v1/kids/sessions", json={"owned_book_id": book_id, "minutes": 20})
	_override_as(library_id, child_b, "child", kids_mode_enabled=True)
	await client.post("/v1/kids/sessions", json={"owned_book_id": book_id, "minutes": 30})

	response = await client.get(f"/v1/kids/challenges/{challenge_id}/progress")
	assert response.status_code == 200
	body = response.json()
	assert body["current"] == 50
	# Cooperative — no per-member breakdown anywhere in the response.
	assert set(body.keys()) == {"challenge", "current"}


async def test_progress_counts_sessions_metric(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/challenges", json=_challenge_body(metric="sessions", target=5))
	challenge_id = created.json()["id"]

	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)
	await client.post("/v1/kids/sessions", json={"owned_book_id": book_id, "minutes": 10})
	await client.post("/v1/kids/sessions", json={"owned_book_id": book_id, "minutes": 15})

	response = await client.get(f"/v1/kids/challenges/{challenge_id}/progress")
	assert response.json()["current"] == 2


async def test_progress_excludes_sessions_outside_the_window(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	today = date.today()
	body = {
		"title": "Short window",
		"metric": "minutes",
		"target": 100,
		"starts_on": today.isoformat(),
		"ends_on": today.isoformat(),
	}
	created = await client.post("/v1/kids/challenges", json=body)
	challenge_id = created.json()["id"]

	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)
	old_date = (today - timedelta(days=10)).isoformat()
	await client.post(
		"/v1/kids/sessions", json={"owned_book_id": book_id, "minutes": 20, "session_date": old_date}
	)

	response = await client.get(f"/v1/kids/challenges/{challenge_id}/progress")
	assert response.json()["current"] == 0


async def test_parent_can_delete_a_challenge(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/challenges", json=_challenge_body())
	challenge_id = created.json()["id"]

	delete = await client.delete(f"/v1/kids/challenges/{challenge_id}")
	assert delete.status_code == 204

	listing = await client.get("/v1/kids/challenges")
	assert listing.json() == []


async def test_child_cannot_delete_a_challenge(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)
	created = await client.post("/v1/kids/challenges", json=_challenge_body())
	challenge_id = created.json()["id"]

	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)
	response = await client.delete(f"/v1/kids/challenges/{challenge_id}")
	assert response.status_code == 403


async def test_create_challenge_rejects_non_positive_target(client: AsyncClient, library_id: UUID) -> None:
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	response = await client.post("/v1/kids/challenges", json=_challenge_body(target=0))
	assert response.status_code == 422
