from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookClubVote
from app.domain.repositories import BookClubVoteRepository
from app.infrastructure.models.book_club_vote_model import BookClubVoteModel


class SQLAlchemyBookClubVoteRepository(BookClubVoteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookClubVoteModel) -> BookClubVote:
        return BookClubVote(
            id=model.id,
            proposal_id=model.proposal_id,
            user_id=model.user_id,
            created_at=model.created_at,
        )

    async def add(self, vote: BookClubVote) -> BookClubVote:
        model = BookClubVoteModel(id=vote.id, proposal_id=vote.proposal_id, user_id=vote.user_id)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_proposal_and_user(self, proposal_id: UUID, user_id: UUID) -> BookClubVote | None:
        result = await self._session.execute(
            select(BookClubVoteModel).where(
                BookClubVoteModel.proposal_id == proposal_id,
                BookClubVoteModel.user_id == user_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def delete(self, vote: BookClubVote) -> None:
        model = await self._session.get(BookClubVoteModel, vote.id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def list_by_proposals(self, proposal_ids: list[UUID]) -> list[BookClubVote]:
        if not proposal_ids:
            return []
        result = await self._session.execute(
            select(BookClubVoteModel).where(BookClubVoteModel.proposal_id.in_(proposal_ids))
        )
        return [self._to_entity(m) for m in result.scalars().all()]
