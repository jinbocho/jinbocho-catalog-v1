import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from app.application.use_cases.catalog import SendLoanRemindersUseCase
from app.config import settings
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.external import HttpLoanReminderNotifier
from app.infrastructure.repositories import (
	SQLAlchemyBibliographicRecordRepository,
	SQLAlchemyBookLoanRepository,
	SQLAlchemyOwnedBookRepository,
)

logger = logging.getLogger(__name__)


async def _run_loan_reminders(http_client: httpx.AsyncClient) -> None:
	# Own DB session, independent of any request — this runs on a timer, not
	# inside a request lifecycle.
	async with AsyncSessionLocal() as session:
		use_case = SendLoanRemindersUseCase(
			loan_repo=SQLAlchemyBookLoanRepository(session),
			book_repo=SQLAlchemyOwnedBookRepository(session),
			record_repo=SQLAlchemyBibliographicRecordRepository(session),
			notifier=HttpLoanReminderNotifier(http_client),
		)
		try:
			sent = await use_case.execute(settings.loan_reminder_lead_days)
			await session.commit()
			logger.info("Loan reminder job sent %d reminder(s)", sent)
		except Exception:
			await session.rollback()
			logger.exception("Loan reminder job failed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
	http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
	app.state.http_client = http_client

	scheduler = AsyncIOScheduler()
	scheduler.add_job(_run_loan_reminders, trigger=IntervalTrigger(hours=24), args=[http_client])
	scheduler.start()
	# IntervalTrigger's first fire is 24h out by default — also run once now
	# so a fresh deploy doesn't wait a full day for the first reminder pass.
	scheduler.add_job(_run_loan_reminders, args=[http_client])

	yield

	scheduler.shutdown(wait=False)
	await http_client.aclose()
