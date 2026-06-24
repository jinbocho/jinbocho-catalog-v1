import logging
from datetime import timedelta

from app.domain.repositories import (
	BibliographicRecordRepository,
	BookLoanRepository,
	LoanReminderNotifier,
	OwnedBookRepository,
)
from app.utils import utcnow

logger = logging.getLogger(__name__)


class SendLoanRemindersUseCase:
	def __init__(
		self,
		loan_repo: BookLoanRepository,
		book_repo: OwnedBookRepository,
		record_repo: BibliographicRecordRepository,
		notifier: LoanReminderNotifier,
	) -> None:
		self._loan_repo = loan_repo
		self._book_repo = book_repo
		self._record_repo = record_repo
		self._notifier = notifier

	async def execute(self, lead_days: int) -> int:
		"""Notifies families about loans due within ``lead_days``. Returns the
		number of reminders sent. A failure on one loan (missing book/record,
		notifier error) is logged and skipped — it must not block the rest of
		the batch."""
		now = utcnow()
		due_before = now + timedelta(days=lead_days)
		loans = await self._loan_repo.list_due_for_reminder(due_before)

		sent = 0
		for loan in loans:
			try:
				book = await self._book_repo.find_by_id(loan.owned_book_id)
				if book is None:
					logger.warning("Loan reminder skipped: owned book %s not found", loan.owned_book_id)
					continue
				record = await self._record_repo.find_by_id(book.bibliographic_record_id)
				book_title = record.title if record else "Untitled"
				assert loan.due_date is not None  # guaranteed by list_due_for_reminder's filter

				await self._notifier.notify(
					family_id=book.family_id,
					book_title=book_title,
					borrower_name=loan.borrower_name,
					due_date=loan.due_date,
				)
				await self._loan_repo.mark_reminder_sent(loan.id, now)
				sent += 1
			except Exception:
				logger.exception("Loan reminder failed for loan %s", loan.id)
				continue
		return sent
