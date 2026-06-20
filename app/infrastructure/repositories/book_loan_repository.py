from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BookLoan
from app.domain.repositories import BookLoanRepository
from app.infrastructure.models.book_loan_model import BookLoanModel
from app.infrastructure.models.owned_book_model import OwnedBookModel


class SQLAlchemyBookLoanRepository(BookLoanRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookLoanModel) -> BookLoan:
        return BookLoan(
            id=model.id,
            owned_book_id=model.owned_book_id,
            borrower_name=model.borrower_name,
            loaned_at=model.loaned_at,
            due_date=model.due_date,
            returned_at=model.returned_at,
        )

    async def add(self, loan: BookLoan) -> BookLoan:
        model = BookLoanModel(
            id=loan.id,
            owned_book_id=loan.owned_book_id,
            borrower_name=loan.borrower_name,
            due_date=loan.due_date,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def mark_returned(self, loan_id: UUID, returned_at: datetime) -> None:
        result = await self._session.execute(
            select(BookLoanModel).where(BookLoanModel.id == loan_id)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            model.returned_at = returned_at
            await self._session.flush()

    async def get_active_for_book(self, owned_book_id: UUID) -> BookLoan | None:
        result = await self._session.execute(
            select(BookLoanModel).where(
                BookLoanModel.owned_book_id == owned_book_id,
                BookLoanModel.returned_at.is_(None),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_book(self, owned_book_id: UUID) -> list[BookLoan]:
        result = await self._session.execute(
            select(BookLoanModel)
            .where(BookLoanModel.owned_book_id == owned_book_id)
            .order_by(BookLoanModel.loaned_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_active_by_family(self, family_id: UUID) -> list[BookLoan]:
        result = await self._session.execute(
            select(BookLoanModel)
            .join(OwnedBookModel, BookLoanModel.owned_book_id == OwnedBookModel.id)
            .where(
                OwnedBookModel.family_id == family_id,
                BookLoanModel.returned_at.is_(None),
            )
            .order_by(BookLoanModel.loaned_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_all_by_family(self, family_id: UUID) -> list[BookLoan]:
        result = await self._session.execute(
            select(BookLoanModel)
            .join(OwnedBookModel, BookLoanModel.owned_book_id == OwnedBookModel.id)
            .where(OwnedBookModel.family_id == family_id)
            .order_by(BookLoanModel.loaned_at.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def restore(self, loan: BookLoan) -> BookLoan:
        model = await self._session.get(BookLoanModel, loan.id)
        if model is None:
            # No id collision is possible (import always mints a fresh one) —
            # but the same loan (same book, borrower, and date) might already
            # have been restored by a previous import of this same backup.
            existing = await self._session.execute(
                select(BookLoanModel).where(
                    BookLoanModel.owned_book_id == loan.owned_book_id,
                    BookLoanModel.borrower_name == loan.borrower_name,
                    BookLoanModel.loaned_at == loan.loaned_at,
                )
            )
            model = existing.scalars().first()
        if model is None:
            model = BookLoanModel(
                id=loan.id,
                owned_book_id=loan.owned_book_id,
                borrower_name=loan.borrower_name,
                loaned_at=loan.loaned_at,
                due_date=loan.due_date,
                returned_at=loan.returned_at,
            )
            self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
