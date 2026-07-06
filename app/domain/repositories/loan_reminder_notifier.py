from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class LoanReminderNotifier(ABC):
	@abstractmethod
	async def notify(self, library_id: UUID, book_title: str, borrower_name: str, due_date: datetime) -> None: ...
