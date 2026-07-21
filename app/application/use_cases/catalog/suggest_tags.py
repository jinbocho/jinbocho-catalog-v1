from dataclasses import dataclass
from uuid import UUID

from app.domain.repositories import BibliographicRecordRepository, TagSuggester


@dataclass
class SuggestTagsOutput:
    tags: list[str]


class SuggestTagsUseCase:
    def __init__(
        self,
        record_repo: BibliographicRecordRepository,
        tag_suggester: TagSuggester,
    ) -> None:
        self._record_repo = record_repo
        self._tag_suggester = tag_suggester

    async def execute(
        self, record_id: UUID, library_id: UUID, reader_language: str | None = None
    ) -> SuggestTagsOutput:
        record = await self._record_repo.find_by_id(record_id)
        if not record:
            raise LookupError("Bibliographic record not found")
        if record.library_id != library_id:
            raise PermissionError("Bibliographic record does not belong to this library")

        result = await self._tag_suggester.suggest(
            title=record.title,
            main_author=record.main_author,
            genre=record.genre,
            reader_language=reader_language,
        )
        return SuggestTagsOutput(tags=result.tags)
