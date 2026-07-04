import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import Section
from app.domain.repositories import BookcaseRepository, SectionRepository
from app.utils import utcnow

from ..bookcase.read import _get_bookcase_for_family

logger = logging.getLogger(__name__)


@dataclass
class CreateSectionInput:
	family_id: UUID
	bookcase_id: UUID
	section_index: int
	label: str | None = None


class CreateSectionUseCase:
	def __init__(self, section_repo: SectionRepository, bookcase_repo: BookcaseRepository) -> None:
		self._section_repo = section_repo
		self._bookcase_repo = bookcase_repo

	async def execute(self, inp: CreateSectionInput) -> Section:
		await _get_bookcase_for_family(self._bookcase_repo, inp.bookcase_id, inp.family_id)
		saved = await self._section_repo.save(
			Section(
				bookcase_id=inp.bookcase_id,
				section_index=inp.section_index,
				label=inp.label,
				created_at=utcnow(),
				updated_at=utcnow(),
			)
		)
		logger.info("Section %s created in family %s", saved.id, inp.family_id)
		return saved
