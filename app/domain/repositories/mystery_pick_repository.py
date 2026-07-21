from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import MysteryPick


class MysteryPickRepository(ABC):
    @abstractmethod
    async def add(self, pick: MysteryPick) -> MysteryPick: ...

    @abstractmethod
    async def find_by_id(self, pick_id: UUID) -> MysteryPick | None: ...

    @abstractmethod
    async def save(self, pick: MysteryPick) -> MysteryPick: ...

    @abstractmethod
    async def list_by_child(self, child_user_id: UUID, library_id: UUID) -> list[MysteryPick]: ...
