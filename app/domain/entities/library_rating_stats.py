from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.domain.entities.book_rating import BookRating


@dataclass(frozen=True)
class LibraryRatingStats:
    owned_book_id: UUID
    total: int
    average: float | None
    distribution: dict[int, int]  # star value (1..5) → count

    @classmethod
    def from_ratings(cls, owned_book_id: UUID, ratings: list[BookRating]) -> LibraryRatingStats:
        distribution = {star: 0 for star in range(1, 6)}
        for r in ratings:
            distribution[r.rating] += 1
        total = len(ratings)
        average = round(sum(r.rating for r in ratings) / total, 2) if total else None
        return cls(
            owned_book_id=owned_book_id,
            total=total,
            average=average,
            distribution=distribution,
        )
