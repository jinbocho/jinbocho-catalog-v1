from dataclasses import dataclass
from uuid import UUID

from app.application.services import fetch_all_pages
from app.domain.repositories import (
	BibliographicRecordRepository,
	BookcaseRepository,
	BookHistoryRepository,
	OwnedBookRepository,
	RemovedMemberRepository,
	RoomRepository,
)


@dataclass
class DeleteFamilyDataOutput:
	rooms_deleted: int
	bookcases_deleted: int
	records_deleted: int
	owned_books_deleted: int
	removed_members_deleted: int


class DeleteFamilyDataUseCase:
	"""Permanently wipes every row this service holds for one family — the
	catalog-service half of the "delete my account" feature (the auth-service
	half deletes the Family/User rows in its own database; the two databases
	have no FK between them, so each side must clean up its own data).

	Deletion order matters — it exists to satisfy FK constraints without
	relying on cascades that don't exist for every relationship:
	  1. book_history has no FK/family_id at all, so it can only be reached by
	     joining against owned_books *before* those are deleted.
	  2. owned_books are deleted next — book_reads/book_loans cascade
	     automatically at the DB level (ON DELETE CASCADE).
	  3. bibliographic_records can only be deleted once no owned_book
	     references them (RESTRICT).
	  4. bookcases are deleted next — sections/shelves cascade automatically.
	  5. rooms can only be deleted once no bookcase references them (RESTRICT).
	  6. removed_members has no dependents — order doesn't matter, done last.
	Excludes IsbnLookupCache on purpose: it's a global cache, not family data.
	"""

	def __init__(
		self,
		room_repo: RoomRepository,
		bookcase_repo: BookcaseRepository,
		record_repo: BibliographicRecordRepository,
		book_repo: OwnedBookRepository,
		book_history_repo: BookHistoryRepository,
		removed_member_repo: RemovedMemberRepository,
	) -> None:
		self._room_repo = room_repo
		self._bookcase_repo = bookcase_repo
		self._record_repo = record_repo
		self._book_repo = book_repo
		self._book_history_repo = book_history_repo
		self._removed_member_repo = removed_member_repo

	async def execute(self, family_id: UUID) -> DeleteFamilyDataOutput:
		book_ids = [book.id for book in await fetch_all_pages(
			lambda limit, offset: self._book_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		)]
		await self._book_history_repo.delete_by_owned_book_ids(book_ids)

		owned_books_deleted = len(book_ids)
		await self._book_repo.delete_all_by_family(family_id)

		records_deleted = len(await fetch_all_pages(
			lambda limit, offset: self._record_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		))
		await self._record_repo.delete_all_by_family(family_id)

		bookcases_deleted = len(await fetch_all_pages(
			lambda limit, offset: self._bookcase_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		))
		await self._bookcase_repo.delete_all_by_family(family_id)

		rooms_deleted = len(await fetch_all_pages(
			lambda limit, offset: self._room_repo.find_all_by_family(family_id, limit=limit, offset=offset)
		))
		await self._room_repo.delete_all_by_family(family_id)

		removed_members_deleted = len(await self._removed_member_repo.find_all_by_family(family_id))
		await self._removed_member_repo.delete_all_by_family(family_id)

		return DeleteFamilyDataOutput(
			rooms_deleted=rooms_deleted,
			bookcases_deleted=bookcases_deleted,
			records_deleted=records_deleted,
			owned_books_deleted=owned_books_deleted,
			removed_members_deleted=removed_members_deleted,
		)
