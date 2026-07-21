from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient

from app.api.dependencies import get_current_user_payload, get_discussion_generator
from app.domain.repositories.discussion_generator import DiscussionBookContext, DiscussionQuestionGenerator
from app.main import app


class FakeDiscussionGenerator(DiscussionQuestionGenerator):
	def __init__(self, questions: list[str]) -> None:
		self._questions = questions
		self.call_count = 0
		self.last_ctx: DiscussionBookContext | None = None

	async def generate(self, ctx: DiscussionBookContext) -> list[str]:
		self.call_count += 1
		self.last_ctx = ctx
		return self._questions


def _override_as(
	library_id: UUID, user_id: UUID, role: str, kids_mode_enabled: bool, language: str | None = None
) -> None:
	async def _override() -> dict[str, Any]:
		payload: dict[str, Any] = {
			"library_id": str(library_id),
			"sub": str(user_id),
			"role": role,
			"kids_mode_enabled": kids_mode_enabled,
		}
		if language is not None:
			payload["language"] = language
		return payload

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


_SAMPLE_QUESTIONS = ["What do you think happens next?", "Would you have done the same as Wilbur?"]


async def test_get_discussion_requires_kids_mode_enabled(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	app.dependency_overrides[get_discussion_generator] = lambda: FakeDiscussionGenerator(_SAMPLE_QUESTIONS)
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=False)

	response = await client.get(f"/v1/kids/books/{book_id}/discussion")
	assert response.status_code == 403


async def test_get_discussion_requires_parent_role(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	app.dependency_overrides[get_discussion_generator] = lambda: FakeDiscussionGenerator(_SAMPLE_QUESTIONS)
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	response = await client.get(f"/v1/kids/books/{book_id}/discussion")
	assert response.status_code == 403


async def test_get_discussion_generates_and_returns_questions(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	fake = FakeDiscussionGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_discussion_generator] = lambda: fake
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	response = await client.get(f"/v1/kids/books/{book_id}/discussion")
	assert response.status_code == 200
	assert response.json()["questions"] == _SAMPLE_QUESTIONS
	assert fake.call_count == 1


async def test_get_discussion_caches_and_does_not_regenerate(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	fake = FakeDiscussionGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_discussion_generator] = lambda: fake
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	first = await client.get(f"/v1/kids/books/{book_id}/discussion")
	second = await client.get(f"/v1/kids/books/{book_id}/discussion")

	assert first.json()["questions"] == second.json()["questions"]
	assert fake.call_count == 1


async def test_get_discussion_passes_reader_age_band_through(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	fake = FakeDiscussionGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_discussion_generator] = lambda: fake
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True)

	await client.get(f"/v1/kids/books/{book_id}/discussion", params={"reader_age_band": "emerging"})

	assert fake.last_ctx is not None
	assert fake.last_ctx.reader_age_band == "emerging"


async def test_get_discussion_passes_reader_language_from_jwt(client: AsyncClient, library_id: UUID) -> None:
	"""The parent's own UI language (JWT claim), not the book's bibliographic
	language, must reach the generator — see DiscussionBookContext.reader_language."""
	book_id = await _create_book(client)
	fake = FakeDiscussionGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_discussion_generator] = lambda: fake
	_override_as(library_id, uuid4(), "admin", kids_mode_enabled=True, language="fr")

	await client.get(f"/v1/kids/books/{book_id}/discussion")

	assert fake.last_ctx is not None
	assert fake.last_ctx.reader_language == "fr"
