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
		self.room_repo = room_repo
		self.bookcase_repo = bookcase_repo
		self.section_repo = section_repo
		self.shelf_repo = shelf_repo

	async def validate(
		self,
		family_id: UUID,
		room_id: UUID,
		bookcase_id: UUID,
		section_id: UUID,
		shelf_id: UUID,
	) -> ResolvedPosition:
		room = await self.room_repo.find_by_id(room_id)
		if not room or room.family_id != family_id:
			raise LookupError("Room not found or does not belong to this family")

		bookcase = await self.bookcase_repo.find_by_id(bookcase_id)
		if not bookcase or bookcase.family_id != family_id or bookcase.room_id != room_id:
			raise LookupError("Bookcase not found or does not belong to this room")

		section = await self.section_repo.find_by_id(section_id)
		if not section or section.bookcase_id != bookcase_id:
			raise LookupError("Section not found or does not belong to this bookcase")

		shelf = await self.shelf_repo.find_by_id(shelf_id)
		if not shelf or shelf.section_id != section_id:
			raise LookupError("Shelf not found or does not belong to this section")

		return ResolvedPosition(
			room=room,
			bookcase_id=bookcase_id,
			section_id=section_id,
			shelf_id=shelf_id,
		)
