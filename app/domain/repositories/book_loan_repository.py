from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.entities import BookLoan


class BookLoanRepository(ABC):
    @abstractmethod
    async def add(self, loan: "BookLoan") -> "BookLoan": ...

    @abstractmethod
    async def mark_returned(self, loan_id: UUID, returned_at: datetime) -> None: ...

    @abstractmethod
    async def get_active_for_book(self, owned_book_id: UUID) -> "BookLoan | None": ...

    @abstractmethod
    async def list_by_book(self, owned_book_id: UUID) -> list["BookLoan"]: ...

    @abstractmethod
    async def list_active_by_family(self, family_id: UUID) -> list["BookLoan"]: ...

    @abstractmethod
    async def list_due_for_reminder(self, due_before: datetime) -> list["BookLoan"]:
        """Active, not-yet-reminded loans with a due_date at or before
        ``due_before`` — candidates for the loan-reminder email job."""
        ...

    @abstractmethod
    async def mark_reminder_sent(self, loan_id: UUID, sent_at: datetime) -> None: ...

    @abstractmethod
    async def find_all_by_family(self, family_id: UUID) -> list["BookLoan"]:
        """All loans (active and returned) — for a full library export, unlike
        list_active_by_family which only covers what's currently lent out."""
        ...

    @abstractmethod
    async def restore(self, loan: "BookLoan") -> "BookLoan":
        """Upsert preserving id/loaned_at/returned_at verbatim — for library
        import, unlike add() which always stamps loaned_at as now and never
        sets returned_at."""
        ...
