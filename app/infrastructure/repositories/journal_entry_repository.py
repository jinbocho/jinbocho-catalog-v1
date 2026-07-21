from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import JournalEntry, JournalPromptKind
from app.domain.repositories import JournalEntryRepository
from app.infrastructure.models.journal_entry_model import JournalEntryModel
from app.infrastructure.models.owned_book_model import OwnedBookModel


class SQLAlchemyJournalEntryRepository(JournalEntryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: JournalEntryModel) -> JournalEntry:
        return JournalEntry(
            id=model.id,
            owned_book_id=model.owned_book_id,
            user_id=model.user_id,
            text=model.text,
            prompt_kind=JournalPromptKind(model.prompt_kind),
            emoji=model.emoji,
            session_id=model.session_id,
            created_at=model.created_at,
        )

    async def add(self, entry: JournalEntry) -> JournalEntry:
        model = JournalEntryModel(
            id=entry.id,
            owned_book_id=entry.owned_book_id,
            user_id=entry.user_id,
            text=entry.text,
            prompt_kind=entry.prompt_kind.value,
            emoji=entry.emoji,
            session_id=entry.session_id,
            created_at=entry.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def list_by_user_and_library(self, user_id: UUID, library_id: UUID) -> list[JournalEntry]:
        result = await self._session.execute(
            select(JournalEntryModel)
            .join(OwnedBookModel, JournalEntryModel.owned_book_id == OwnedBookModel.id)
            .where(JournalEntryModel.user_id == user_id, OwnedBookModel.library_id == library_id)
            .order_by(JournalEntryModel.created_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]
