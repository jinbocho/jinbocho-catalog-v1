from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Room
from app.domain.repositories import BookcaseRepository, RoomRepository, SectionRepository, ShelfRepository


@dataclass
class ResolvedPosition:
	room: Room
	bookcase_id: UUID
	section_id: UUID
	shelf_id: UUID


class PositionValidationService:
	def __init__(
		self,
		room_repo: RoomRepository,
		bookcase_repo: BookcaseRepository,
		section_repo: SectionRepository,
		shelf_repo: ShelfRepository,
	):
		self._room_repo = room_repo
		self._bookcase_repo = bookcase_repo
		self._section_repo = section_repo
		self._shelf_repo = shelf_repo

	async def validate(
		self,
		library_id: UUID,
		room_id: UUID,
		bookcase_id: UUID,
		section_id: UUID,
		shelf_id: UUID,
	) -> ResolvedPosition:
		room = await self._room_repo.find_by_id(room_id)
		if not room:
			raise LookupError("Room not found")
		if room.library_id != library_id:
			raise PermissionError("Room does not belong to this library")

		bookcase = await self._bookcase_repo.find_by_id(bookcase_id)
		if not bookcase:
			raise LookupError("Bookcase not found")
		if bookcase.library_id != library_id:
			raise PermissionError("Bookcase does not belong to this library")
		if bookcase.room_id != room_id:
			raise LookupError("Bookcase does not belong to this room")

		section = await self._section_repo.find_by_id(section_id)
		if not section or section.bookcase_id != bookcase_id:
			raise LookupError("Section not found or does not belong to this bookcase")

		shelf = await self._shelf_repo.find_by_id(shelf_id)
		if not shelf or shelf.section_id != section_id:
			raise LookupError("Shelf not found or does not belong to this section")

		return ResolvedPosition(
			room=room,
			bookcase_id=bookcase_id,
			section_id=section_id,
			shelf_id=shelf_id,
		)
