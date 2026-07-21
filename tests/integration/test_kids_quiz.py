from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient

from app.api.dependencies import get_current_user_payload, get_quiz_generator
from app.domain.repositories.quiz_generator import GeneratedQuizQuestion, QuizBookContext, QuizGenerator
from app.main import app


class FakeQuizGenerator(QuizGenerator):
	def __init__(self, questions: list[GeneratedQuizQuestion]) -> None:
		self._questions = questions
		self.call_count = 0
		self.last_ctx: QuizBookContext | None = None

	async def generate(self, ctx: QuizBookContext) -> list[GeneratedQuizQuestion]:
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


_SAMPLE_QUESTIONS = [
	GeneratedQuizQuestion(
		prompt="What kind of animal is Wilbur?", choices=["Pig", "Spider", "Goose", "Rat"], correct_index=0
	),
	GeneratedQuizQuestion(
		prompt="Who is Wilbur's friend?", choices=["Charlotte", "Templeton", "Fern", "Homer"], correct_index=0
	),
]


async def test_generate_quiz_requires_kids_mode_enabled(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	app.dependency_overrides[get_quiz_generator] = lambda: FakeQuizGenerator(_SAMPLE_QUESTIONS)
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=False)

	response = await client.post(f"/v1/kids/books/{book_id}/quiz/generate", json={"num_questions": 5})
	assert response.status_code == 403


async def test_generate_quiz_uses_ai_and_sanitizes_response(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	fake = FakeQuizGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_quiz_generator] = lambda: fake
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	response = await client.post(f"/v1/kids/books/{book_id}/quiz/generate", json={"num_questions": 5})
	assert response.status_code == 200
	questions = response.json()
	assert len(questions) == 2
	assert questions[0]["prompt"] == "What kind of animal is Wilbur?"
	assert questions[0]["source"] == "ai"
	assert "correct_index" not in questions[0]


async def test_generate_quiz_passes_reader_language_from_jwt(client: AsyncClient, library_id: UUID) -> None:
	"""The requester's own UI language (JWT claim), not the book's
	bibliographic language, must reach the generator — see QuizBookContext.reader_language."""
	book_id = await _create_book(client)
	fake = FakeQuizGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_quiz_generator] = lambda: fake
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True, language="it")

	response = await client.post(f"/v1/kids/books/{book_id}/quiz/generate", json={"num_questions": 5})
	assert response.status_code == 200
	assert fake.last_ctx is not None
	assert fake.last_ctx.reader_language == "it"


async def test_generate_quiz_does_not_regenerate_when_questions_exist(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	fake = FakeQuizGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_quiz_generator] = lambda: fake
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	first = await client.post(f"/v1/kids/books/{book_id}/quiz/generate", json={"num_questions": 5})
	assert first.status_code == 200
	assert fake.call_count == 1

	second = await client.post(f"/v1/kids/books/{book_id}/quiz/generate", json={"num_questions": 5})
	assert second.status_code == 200
	assert fake.call_count == 1  # not called again
	assert [q["id"] for q in second.json()] == [q["id"] for q in first.json()]


async def test_generate_quiz_with_extra_context_regenerates_and_appends(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	fake = FakeQuizGenerator(_SAMPLE_QUESTIONS)
	app.dependency_overrides[get_quiz_generator] = lambda: fake
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	first = await client.post(f"/v1/kids/books/{book_id}/quiz/generate", json={"num_questions": 5})
	assert fake.call_count == 1
	first_ids = {q["id"] for q in first.json()}

	more_questions = [
		GeneratedQuizQuestion(prompt="What does Charlotte weave?", choices=["A web", "A basket"], correct_index=0),
	]
	fake._questions = more_questions  # noqa: SLF001 - test-only mutation of the fake

	second = await client.post(
		f"/v1/kids/books/{book_id}/quiz/generate",
		json={"num_questions": 5, "extra_context": "Focus on the barn animals"},
	)
	assert second.status_code == 200
	assert fake.call_count == 2  # regenerated despite existing questions
	assert fake.last_ctx is not None
	assert fake.last_ctx.extra_context == "Focus on the barn animals"

	second_ids = {q["id"] for q in second.json()}
	assert first_ids <= second_ids  # original questions still present
	assert len(second_ids) == 3  # 2 original + 1 newly appended


async def test_generate_quiz_falls_back_to_empty_when_ai_disabled(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	app.dependency_overrides[get_quiz_generator] = lambda: FakeQuizGenerator([])
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	response = await client.post(f"/v1/kids/books/{book_id}/quiz/generate", json={"num_questions": 5})
	assert response.status_code == 200
	assert response.json() == []


async def test_create_manual_quiz_question_requires_parent_role(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	_override_as(library_id, uuid4(), "child", kids_mode_enabled=True)

	response = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "What color is the barn?", "choices": ["Red", "Blue"], "correct_index": 0},
	)
	assert response.status_code == 403


async def test_create_manual_quiz_question_as_parent(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)

	response = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "What color is the barn?", "choices": ["Red", "Blue"], "correct_index": 0},
	)
	assert response.status_code == 201
	body = response.json()
	assert body["correct_index"] == 0
	assert body["source"] == "manual"


async def test_submit_quiz_attempt_scores_correctly(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)

	q1 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q1", "choices": ["A", "B"], "correct_index": 0},
	)
	q2 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q2", "choices": ["A", "B"], "correct_index": 1},
	)
	q1_id = q1.json()["id"]
	q2_id = q2.json()["id"]

	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	response = await client.post(
		f"/v1/kids/books/{book_id}/quiz/attempts",
		json={"answers": {q1_id: 0, q2_id: 0}},  # second answer wrong
	)
	assert response.status_code == 201
	body = response.json()
	assert body["score"] == 1
	assert body["total"] == 2
	assert body["passed"] is False  # 50% < 70% threshold
	assert body["user_id"] == str(child_id)


async def test_child_cannot_list_another_childs_quiz_attempts(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	q1 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q1", "choices": ["A", "B"], "correct_index": 0},
	)
	q1_id = q1.json()["id"]

	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	await client.post(f"/v1/kids/books/{book_id}/quiz/attempts", json={"answers": {q1_id: 0}})

	other_child_id = uuid4()
	_override_as(library_id, other_child_id, "child", kids_mode_enabled=True)
	response = await client.get("/v1/kids/attempts", params={"user_id": str(child_id)})
	assert response.status_code == 403


async def test_parent_can_list_a_childs_quiz_attempts(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	q1 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q1", "choices": ["A", "B"], "correct_index": 0},
	)
	q1_id = q1.json()["id"]

	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	await client.post(f"/v1/kids/books/{book_id}/quiz/attempts", json={"answers": {q1_id: 0}})

	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	response = await client.get("/v1/kids/attempts", params={"user_id": str(child_id)})
	assert response.status_code == 200
	assert len(response.json()) == 1


async def test_attempt_detail_marks_correct_and_wrong_answers(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	q1 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q1", "choices": ["A", "B"], "correct_index": 0},
	)
	q2 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q2", "choices": ["A", "B"], "correct_index": 1},
	)
	q1_id = q1.json()["id"]
	q2_id = q2.json()["id"]

	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	submit_resp = await client.post(
		f"/v1/kids/books/{book_id}/quiz/attempts",
		json={"answers": {q1_id: 0, q2_id: 0}},  # q1 correct, q2 wrong
	)
	attempt_id = submit_resp.json()["id"]

	detail_resp = await client.get(f"/v1/kids/attempts/{attempt_id}")
	assert detail_resp.status_code == 200
	body = detail_resp.json()
	assert body["score"] == 1
	assert body["total"] == 2
	answers_by_question = {a["question_id"]: a for a in body["answers"]}
	assert answers_by_question[q1_id]["is_correct"] is True
	assert answers_by_question[q1_id]["correct_index"] == 0
	assert answers_by_question[q2_id]["is_correct"] is False
	assert answers_by_question[q2_id]["selected_index"] == 0
	assert answers_by_question[q2_id]["correct_index"] == 1


async def test_attempt_detail_forbidden_for_unrelated_child(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	q1 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q1", "choices": ["A", "B"], "correct_index": 0},
	)
	q1_id = q1.json()["id"]

	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	submit_resp = await client.post(f"/v1/kids/books/{book_id}/quiz/attempts", json={"answers": {q1_id: 0}})
	attempt_id = submit_resp.json()["id"]

	other_child_id = uuid4()
	_override_as(library_id, other_child_id, "child", kids_mode_enabled=True)
	response = await client.get(f"/v1/kids/attempts/{attempt_id}")
	assert response.status_code == 403


async def test_attempt_detail_visible_to_parent(client: AsyncClient, library_id: UUID) -> None:
	book_id = await _create_book(client)
	parent_id = uuid4()
	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	q1 = await client.post(
		f"/v1/kids/books/{book_id}/quiz/questions",
		json={"prompt": "Q1", "choices": ["A", "B"], "correct_index": 0},
	)
	q1_id = q1.json()["id"]

	child_id = uuid4()
	_override_as(library_id, child_id, "child", kids_mode_enabled=True)
	submit_resp = await client.post(f"/v1/kids/books/{book_id}/quiz/attempts", json={"answers": {q1_id: 0}})
	attempt_id = submit_resp.json()["id"]

	_override_as(library_id, parent_id, "admin", kids_mode_enabled=True)
	response = await client.get(f"/v1/kids/attempts/{attempt_id}")
	assert response.status_code == 200
	assert response.json()["id"] == attempt_id
