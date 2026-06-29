from abc import ABC, abstractmethod
from typing import Any


class BookSearchProvider(ABC):
    @abstractmethod
    async def search(
        self,
        title: str | None,
        author: str | None,
        max_results: int,
    ) -> list[dict[str, Any]]: ...
