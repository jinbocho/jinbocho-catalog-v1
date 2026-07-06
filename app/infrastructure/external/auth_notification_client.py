import logging
from datetime import datetime
from uuid import UUID

import httpx

from app.config import settings
from app.domain.repositories import LoanReminderNotifier

logger = logging.getLogger(__name__)


class HttpLoanReminderNotifier(LoanReminderNotifier):
	"""Asks auth-service to email the library about a loan due soon.

	catalog-service owns BookLoan but not user emails/languages — those live
	in auth-service's own DB. Cross-service call instead of a shared table,
	per the "HTTP-only communication, one DB per service" decision."""

	def __init__(self, http_client: httpx.AsyncClient) -> None:
		self._http_client = http_client

	async def notify(self, library_id: UUID, book_title: str, borrower_name: str, due_date: datetime) -> None:
		response = await self._http_client.post(
			f"{settings.auth_service_url}/v1/internal/notifications/loan-reminder",
			headers={"X-Internal-Token": settings.internal_service_token},
			json={
				"library_id": str(library_id),
				"book_title": book_title,
				"borrower_name": borrower_name,
				"due_date": due_date.isoformat(),
			},
		)
		if response.status_code >= 300:
			logger.error(
				"auth-service rejected loan reminder for library %s: %s %s",
				library_id,
				response.status_code,
				response.text,
			)
			response.raise_for_status()
