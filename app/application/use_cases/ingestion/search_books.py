from typing import Any

from app.domain.repositories import BookSearchProvider


class SearchBooksUseCase:
    def __init__(self, provider: BookSearchProvider) -> None:
        self._provider = provider

    async def execute(self, title: str | None, author: str | None, max_results: int = 10) -> list[dict[str, Any]]:
        if not title and not author:
            raise ValueError("At least one of title or author must be provided")
        return await self._provider.search(title, author, max_results)
