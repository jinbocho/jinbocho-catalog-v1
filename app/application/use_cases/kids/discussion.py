import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import DiscussionQuestionSet
from app.domain.repositories import (
	BibliographicRecordRepository,
	DiscussionBookContext,
	DiscussionQuestionGenerator,
	DiscussionQuestionSetRepository,
	OwnedBookRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class GetDiscussionQuestionsInput:
	owned_book_id: UUID
	library_id: UUID
	kids_mode_enabled: bool
	reader_age_band: str | None = None
	reader_language: str | None = None
	num_questions: int = 3


class GetDiscussionQuestionsUseCase:
	"""Get-or-generate, one cached set per book (KID-04): if questions already
	exist, returns them as-is rather than repaying the LLM on every parent
	dashboard view."""

	def __init__(
		self,
		book_repo: OwnedBookRepository,
		record_repo: BibliographicRecordRepository,
		question_set_repo: DiscussionQuestionSetRepository,
		generator: DiscussionQuestionGenerator,
	) -> None:
		self._book_repo = book_repo
		self._record_repo = record_repo
		self._question_set_repo = question_set_repo
		self._generator = generator

	async def execute(self, input: GetDiscussionQuestionsInput) -> list[str]:
		if not input.kids_mode_enabled:
			raise PermissionError("Kids mode is not enabled for this library")
		book = await self._book_repo.find_by_id(input.owned_book_id)
		if not book:
			raise LookupError("Book not found")
		if book.library_id != input.library_id:
			raise PermissionError("Book does not belong to this library")

		existing = await self._question_set_repo.find_by_book(input.owned_book_id)
		if existing is not None:
			return existing.questions

		record = await self._record_repo.find_by_id(book.bibliographic_record_id)
		if not record:
			return []

		questions = await self._generator.generate(
			DiscussionBookContext(
				title=record.title,
				main_author=record.main_author,
				genre=record.genre,
				incipit=record.incipit,
				language=record.language,
				num_questions=input.num_questions,
				reader_age_band=input.reader_age_band,
				reader_language=input.reader_language,
			)
		)
		if not questions:
			return []

		await self._question_set_repo.save(
			DiscussionQuestionSet(owned_book_id=input.owned_book_id, questions=questions)
		)
		logger.info("Discussion questions generated for book %s in library %s", book.id, input.library_id)
		return questions
