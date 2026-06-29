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

    async def execute(self, record_id: UUID, family_id: UUID) -> SuggestTagsOutput:
        record = await self._record_repo.find_by_id(record_id)
        if not record or record.family_id != family_id:
            raise LookupError("Bibliographic record not found")

        result = await self._tag_suggester.suggest(
            title=record.title,
            main_author=record.main_author,
            genre=record.genre,
        )
        return SuggestTagsOutput(tags=result.tags)
