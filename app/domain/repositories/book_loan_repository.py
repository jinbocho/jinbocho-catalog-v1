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
