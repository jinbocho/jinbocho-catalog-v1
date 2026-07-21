from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TagSuggestion:
    tags: list[str]


class TagSuggester(ABC):
    @abstractmethod
    async def suggest(
        self,
        title: str,
        main_author: str | None,
        genre: str | None,
        reader_language: str | None = None,
    ) -> TagSuggestion: ...
