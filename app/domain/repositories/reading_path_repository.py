from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import ReadingPath


class ReadingPathRepository(ABC):
    @abstractmethod
    async def add(self, path: ReadingPath) -> ReadingPath: ...

    @abstractmethod
    async def find_by_id(self, path_id: UUID) -> ReadingPath | None: ...

    @abstractmethod
    async def list_by_library(self, library_id: UUID) -> list[ReadingPath]: ...

    @abstractmethod
    async def delete(self, path_id: UUID) -> None: ...
