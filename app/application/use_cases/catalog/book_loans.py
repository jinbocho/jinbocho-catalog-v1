import logging
from datetime import UTC, datetime
from uuid import UUID

from app.domain.entities import BookLoan
from app.domain.repositories import BookLoanRepository, OwnedBookRepository

logger = logging.getLogger(__name__)


class LendBookUseCase:
    def __init__(self, book_repo: OwnedBookRepository, loan_repo: BookLoanRepository) -> None:
        self._book_repo = book_repo
        self._loan_repo = loan_repo

    async def execute(
        self,
        book_id: UUID,
        library_id: UUID,
        borrower_name: str,
        due_date: datetime | None = None,
        borrower_user_id: UUID | None = None,
    ) -> BookLoan:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        active = await self._loan_repo.get_active_for_book(book_id)
        if active:
            raise ValueError("Book is already on loan")
        loan = BookLoan(
            owned_book_id=book_id, borrower_name=borrower_name, borrower_user_id=borrower_user_id, due_date=due_date,
        )
        saved = await self._loan_repo.add(loan)
        logger.info("Book %s lent to %r by library %s", book_id, borrower_name, library_id)
        return saved


class ReturnBookUseCase:
    def __init__(self, book_repo: OwnedBookRepository, loan_repo: BookLoanRepository) -> None:
        self._book_repo = book_repo
        self._loan_repo = loan_repo

    async def execute(self, book_id: UUID, library_id: UUID) -> BookLoan:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        active = await self._loan_repo.get_active_for_book(book_id)
        if not active:
            raise LookupError("No active loan for this book")
        returned_at = datetime.now(UTC)
        await self._loan_repo.mark_returned(active.id, returned_at)
        logger.info("Book %s loan %s returned in library %s", book_id, active.id, library_id)
        return BookLoan(
            id=active.id,
            owned_book_id=active.owned_book_id,
            borrower_name=active.borrower_name,
            borrower_user_id=active.borrower_user_id,
            loaned_at=active.loaned_at,
            due_date=active.due_date,
            returned_at=returned_at,
        )


class ListBookLoansUseCase:
    def __init__(self, book_repo: OwnedBookRepository, loan_repo: BookLoanRepository) -> None:
        self._book_repo = book_repo
        self._loan_repo = loan_repo

    async def execute(self, book_id: UUID, library_id: UUID) -> list[BookLoan]:
        book = await self._book_repo.find_by_id(book_id)
        if not book:
            raise LookupError("Book not found")
        if book.library_id != library_id:
            raise PermissionError("Book does not belong to this library")
        return await self._loan_repo.list_by_book(book_id)


class ListActiveLibraryLoansUseCase:
    def __init__(self, loan_repo: BookLoanRepository) -> None:
        self._loan_repo = loan_repo

    async def execute(self, library_id: UUID) -> list[BookLoan]:
        return await self._loan_repo.list_active_by_library(library_id)


class ListAllLibraryLoansUseCase:
    def __init__(self, loan_repo: BookLoanRepository) -> None:
        self._loan_repo = loan_repo

    async def execute(self, library_id: UUID) -> list[BookLoan]:
        return await self._loan_repo.find_all_by_library(library_id)
