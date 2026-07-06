from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.application.use_cases.catalog import SendLoanRemindersUseCase
from app.domain.entities import BibliographicRecord, BookLoan, OwnedBook
from app.domain.repositories import LoanReminderNotifier
from tests.unit.conftest import (
	MockBibliographicRecordRepository,
	MockBookLoanRepository,
	MockOwnedBookRepository,
)


class FakeNotifier(LoanReminderNotifier):
	def __init__(self, fail_for: set[UUID] | None = None) -> None:
		self.calls: list[tuple[UUID, str, str, datetime]] = []
		self._fail_for = fail_for or set()

	async def notify(self, library_id: UUID, book_title: str, borrower_name: str, due_date: datetime) -> None:
		if library_id in self._fail_for:
			raise RuntimeError("boom")
		self.calls.append((library_id, book_title, borrower_name, due_date))


@pytest.fixture
def library_id() -> UUID:
	return uuid4()


async def _seed_loan(
	loan_repo: MockBookLoanRepository,
	book_repo: MockOwnedBookRepository,
	record_repo: MockBibliographicRecordRepository,
	library_id: UUID,
	due_date: datetime | None,
	borrower_name: str = "Mario",
) -> BookLoan:
	record = BibliographicRecord(library_id=library_id, title="Dune")
	await record_repo.save(record)
	book = OwnedBook(library_id=library_id, bibliographic_record_id=record.id)
	await book_repo.save(book)
	loan = BookLoan(owned_book_id=book.id, borrower_name=borrower_name, due_date=due_date)
	await loan_repo.add(loan)
	return loan


@pytest.mark.asyncio
async def test_sends_reminder_for_loan_due_soon_and_marks_it_sent(library_id: UUID) -> None:
	loan_repo = MockBookLoanRepository()
	book_repo = MockOwnedBookRepository()
	record_repo = MockBibliographicRecordRepository()
	notifier = FakeNotifier()
	loan = await _seed_loan(
		loan_repo, book_repo, record_repo, library_id,
		due_date=datetime.now(UTC) + timedelta(hours=12),
	)

	use_case = SendLoanRemindersUseCase(loan_repo, book_repo, record_repo, notifier)
	sent = await use_case.execute(lead_days=1)

	assert sent == 1
	assert notifier.calls == [(library_id, "Dune", "Mario", loan.due_date)]
	assert loan_repo.loans[loan.id].reminder_sent_at is not None


@pytest.mark.asyncio
async def test_skips_loan_not_yet_due(library_id: UUID) -> None:
	loan_repo = MockBookLoanRepository()
	book_repo = MockOwnedBookRepository()
	record_repo = MockBibliographicRecordRepository()
	notifier = FakeNotifier()
	await _seed_loan(
		loan_repo, book_repo, record_repo, library_id,
		due_date=datetime.now(UTC) + timedelta(days=10),
	)

	use_case = SendLoanRemindersUseCase(loan_repo, book_repo, record_repo, notifier)
	sent = await use_case.execute(lead_days=1)

	assert sent == 0
	assert notifier.calls == []


@pytest.mark.asyncio
async def test_skips_already_reminded_loan(library_id: UUID) -> None:
	loan_repo = MockBookLoanRepository()
	book_repo = MockOwnedBookRepository()
	record_repo = MockBibliographicRecordRepository()
	notifier = FakeNotifier()
	loan = await _seed_loan(
		loan_repo, book_repo, record_repo, library_id,
		due_date=datetime.now(UTC) + timedelta(hours=1),
	)
	await loan_repo.mark_reminder_sent(loan.id, datetime.now(UTC))

	use_case = SendLoanRemindersUseCase(loan_repo, book_repo, record_repo, notifier)
	sent = await use_case.execute(lead_days=1)

	assert sent == 0
	assert notifier.calls == []


@pytest.mark.asyncio
async def test_one_failing_loan_does_not_block_the_rest(library_id: UUID) -> None:
	other_library_id = uuid4()
	loan_repo = MockBookLoanRepository()
	book_repo = MockOwnedBookRepository()
	record_repo = MockBibliographicRecordRepository()
	notifier = FakeNotifier(fail_for={library_id})

	failing_loan = await _seed_loan(
		loan_repo, book_repo, record_repo, library_id,
		due_date=datetime.now(UTC) + timedelta(hours=1), borrower_name="Mario",
	)
	ok_loan = await _seed_loan(
		loan_repo, book_repo, record_repo, other_library_id,
		due_date=datetime.now(UTC) + timedelta(hours=1), borrower_name="Luigi",
	)

	use_case = SendLoanRemindersUseCase(loan_repo, book_repo, record_repo, notifier)
	sent = await use_case.execute(lead_days=1)

	assert sent == 1
	assert [c[2] for c in notifier.calls] == ["Luigi"]
	# The failing loan was not marked as reminded — it'll be retried next run.
	assert loan_repo.loans[failing_loan.id].reminder_sent_at is None
	assert loan_repo.loans[ok_loan.id].reminder_sent_at is not None
