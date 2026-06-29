from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities import BookRating


class BookRatingRepository(ABC):
    @abstractmethod
    async def add(self, rating: BookRating) -> BookRating: ...

    @abstractmethod
    async def save(self, rating: BookRating) -> BookRating: ...

    @abstractmethod
    async def find_by_id(self, rating_id: UUID) -> BookRating | None: ...

    @abstractmethod
    async def find_by_book_and_user(self, owned_book_id: UUID, user_id: UUID) -> BookRating | None: ...

    @abstractmethod
    async def list_by_book(self, owned_book_id: UUID) -> list[BookRating]: ...

    @abstractmethod
    async def list_by_family(self, family_id: UUID) -> list[BookRating]: ...

    @abstractmethod
    async def delete(self, rating: BookRating) -> None: ...

    @abstractmethod
    async def restore(self, rating: BookRating) -> BookRating:
        """Upsert preserving id/timestamps verbatim — for library import."""
        ...
