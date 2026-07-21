from uuid import UUID

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookClubProposal
from app.domain.repositories import BookClubProposalRepository
from app.infrastructure.models.book_club_proposal_model import BookClubProposalModel


class SQLAlchemyBookClubProposalRepository(BookClubProposalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookClubProposalModel) -> BookClubProposal:
        return BookClubProposal(
            id=model.id,
            library_id=model.library_id,
            bibliographic_record_id=model.bibliographic_record_id,
            proposed_by=model.proposed_by,
            note=model.note,
            created_at=model.created_at,
        )

    async def add(self, proposal: BookClubProposal) -> BookClubProposal:
        model = BookClubProposalModel(
            id=proposal.id,
            library_id=proposal.library_id,
            bibliographic_record_id=proposal.bibliographic_record_id,
            proposed_by=proposal.proposed_by,
            note=proposal.note,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, proposal_id: UUID) -> BookClubProposal | None:
        model = await self._session.get(BookClubProposalModel, proposal_id)
        return self._to_entity(model) if model else None

    async def list_by_library(self, library_id: UUID) -> list[BookClubProposal]:
        result = await self._session.execute(
            select(BookClubProposalModel)
            .where(BookClubProposalModel.library_id == library_id)
            .order_by(BookClubProposalModel.created_at.asc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, proposal: BookClubProposal) -> None:
        model = await self._session.get(BookClubProposalModel, proposal.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def delete_all_by_library(self, library_id: UUID) -> None:
        await self._session.execute(
            sa_delete(BookClubProposalModel).where(BookClubProposalModel.library_id == library_id)
        )
        await self._session.flush()
