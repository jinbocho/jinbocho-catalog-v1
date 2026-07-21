import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import BookClubQuestionSet
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookClubCycleRepository,
    BookClubQuestionSetRepository,
    DiscussionBookContext,
    DiscussionQuestionGenerator,
)

logger = logging.getLogger(__name__)

# Book-club prompts favour a slightly longer set than the Kids dinner-table card.
_NUM_QUESTIONS = 5


@dataclass
class GetCycleQuestionsInput:
    cycle_id: UUID
    library_id: UUID
    reader_language: str | None = None


class GetCycleQuestionsUseCase:
    """Get-or-generate, one cached set per cycle (CLUB-08). Reuses the shared
    DiscussionQuestionGenerator port with an adult context (no age band). A
    disabled or failing LLM yields an empty list and stores nothing, so the UI
    simply shows no prompts."""

    def __init__(
        self,
        cycle_repo: BookClubCycleRepository,
        record_repo: BibliographicRecordRepository,
        question_set_repo: BookClubQuestionSetRepository,
        generator: DiscussionQuestionGenerator,
    ) -> None:
        self._cycle_repo = cycle_repo
        self._record_repo = record_repo
        self._question_set_repo = question_set_repo
        self._generator = generator

    async def execute(self, inp: GetCycleQuestionsInput) -> list[str]:
        cycle = await self._cycle_repo.find_by_id(inp.cycle_id)
        if cycle is None:
            raise LookupError("Cycle not found")
        if cycle.library_id != inp.library_id:
            raise PermissionError("Cycle does not belong to this library")

        language = inp.reader_language or ""
        existing = await self._question_set_repo.find_by_cycle_and_language(inp.cycle_id, language)
        if existing is not None:
            return existing.questions

        record = await self._record_repo.find_by_id(cycle.bibliographic_record_id)
        if record is None:
            return []

        questions = await self._generator.generate(
            DiscussionBookContext(
                title=record.title,
                main_author=record.main_author,
                genre=record.genre,
                incipit=record.incipit,
                language=record.language,
                num_questions=_NUM_QUESTIONS,
                reader_age_band=None,
                reader_language=inp.reader_language,
            )
        )
        if not questions:
            return []

        await self._question_set_repo.save(
            BookClubQuestionSet(cycle_id=inp.cycle_id, language=language, questions=questions)
        )
        logger.info("Discussion questions generated for cycle %s in library %s", cycle.id, inp.library_id)
        return questions
