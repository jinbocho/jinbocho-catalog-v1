import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import ReadingPath, ReadingPathSource
from app.domain.repositories import ReadingPathRepository

logger = logging.getLogger(__name__)


@dataclass
class CreateReadingPathInput:
    library_id: UUID
    created_by: UUID
    kids_mode_enabled: bool
    title: str
    book_ids: list[UUID]
    description: str | None = None
    target_band: str | None = None


class CreateReadingPathUseCase:
    """Parent-only (require_parent enforced at the endpoint) — a curated
    sequence built from the family's own catalog, not a generic wishlist."""

    def __init__(self, path_repo: ReadingPathRepository) -> None:
        self._path_repo = path_repo

    async def execute(self, input: CreateReadingPathInput) -> ReadingPath:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        if not input.book_ids:
            raise ValueError("A reading path needs at least one book")

        path = ReadingPath(
            library_id=input.library_id,
            title=input.title,
            book_ids=input.book_ids,
            description=input.description,
            target_band=input.target_band,
            source=ReadingPathSource.MANUAL,
            created_by=input.created_by,
        )
        saved = await self._path_repo.add(path)
        logger.info("Reading path %s created in library %s by %s", saved.id, input.library_id, input.created_by)
        return saved


@dataclass
class ListReadingPathsInput:
    library_id: UUID
    kids_mode_enabled: bool


class ListReadingPathsUseCase:
    """Open to any authenticated library member (child sees their paths,
    parent manages them) — unlike journal/session data, a reading path isn't
    personal to one child."""

    def __init__(self, path_repo: ReadingPathRepository) -> None:
        self._path_repo = path_repo

    async def execute(self, input: ListReadingPathsInput) -> list[ReadingPath]:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        return await self._path_repo.list_by_library(input.library_id)


@dataclass
class DeleteReadingPathInput:
    path_id: UUID
    library_id: UUID
    kids_mode_enabled: bool


class DeleteReadingPathUseCase:
    """Parent-only (require_parent enforced at the endpoint)."""

    def __init__(self, path_repo: ReadingPathRepository) -> None:
        self._path_repo = path_repo

    async def execute(self, input: DeleteReadingPathInput) -> None:
        if not input.kids_mode_enabled:
            raise PermissionError("Kids mode is not enabled for this library")
        path = await self._path_repo.find_by_id(input.path_id)
        if path is None:
            raise LookupError("Reading path not found")
        if path.library_id != input.library_id:
            raise PermissionError("Reading path does not belong to this library")
        await self._path_repo.delete(input.path_id)
        logger.info("Reading path %s deleted from library %s", input.path_id, input.library_id)
