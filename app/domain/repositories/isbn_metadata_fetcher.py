from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class IsbnFetchResult:
    source: str
    metadata: dict[str, Any]


class IsbnMetadataFetcher(ABC):
    @abstractmethod
    async def fetch(self, isbn: str) -> IsbnFetchResult | None: ...
