from abc import ABC, abstractmethod


class EditorialDescriptionProvider(ABC):
    @abstractmethod
    async def fetch(self, isbn: str) -> str | None: ...
