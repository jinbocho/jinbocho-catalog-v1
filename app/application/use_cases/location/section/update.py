from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Section
from app.domain.repositories import BookcaseRepository, SectionRepository
from app.utils import utcnow

from ..bookcase.read import _get_bookcase_for_family
from .read import _get_section_for_family


@dataclass
class UpdateSectionInput:
	section_id: UUID
	family_id: UUID
	bookcase_id: UUID | None = None
	section_index: int | None = None
	label: str | None = None


class UpdateSectionUseCase:
	def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, inp: UpdateSectionInput) -> Section:
		section = await _get_section_for_family(self._section_repo, self._bookcase_repo, inp.section_id, inp.family_id)
		if inp.bookcase_id is not None:
			await _get_bookcase_for_family(self._bookcase_repo, inp.bookcase_id, inp.family_id)
			section.bookcase_id = inp.bookcase_id
		if inp.section_index is not None:
			section.section_index = inp.section_index
		if inp.label is not None:
			section.label = inp.label
		section.updated_at = utcnow()
		return await self._section_repo.save(section)
