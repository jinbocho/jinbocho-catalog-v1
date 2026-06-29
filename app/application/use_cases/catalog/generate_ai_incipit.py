from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.repositories import BibliographicRecordRepository, EditorialDescriptionProvider
from app.infrastructure.external.ai_incipit_client import AiIncipitClient
from app.utils import utcnow


@dataclass
class GenerateAiIncipitOutput:
    text: str | None
    source: str | None
    generated_at: datetime | None


class GenerateAiIncipitUseCase:
    def __init__(
        self,
        record_repo: BibliographicRecordRepository,
        ai_client: AiIncipitClient,
        description_provider: EditorialDescriptionProvider,
    ) -> None:
        self._record_repo = record_repo
        self._ai_client = ai_client
        self._description_provider = description_provider

    async def execute(self, record_id: UUID, family_id: UUID) -> GenerateAiIncipitOutput:
        record = await self._record_repo.find_by_id(record_id)
        if not record or record.family_id != family_id:
            raise LookupError("Bibliographic record not found")

        editorial_description: str | None = None
        if record.isbn:
            editorial_description = await self._description_provider.fetch(record.isbn)

        result = await self._ai_client.generate(
            title=record.title,
            main_author=record.main_author,
            genre=record.genre,
            language=record.language,
            publisher=record.publisher,
            publication_year=record.publication_year,
            editorial_description=editorial_description,
        )

        if not result.text:
            return GenerateAiIncipitOutput(text=None, source=None, generated_at=None)

        record.incipit = result.text
        record.incipit_source = "ai"
        record.incipit_generated_at = utcnow()
        record.updated_at = utcnow()
        saved = await self._record_repo.save(record)
        return GenerateAiIncipitOutput(
            text=saved.incipit,
            source=saved.incipit_source,
            generated_at=saved.incipit_generated_at,
        )
