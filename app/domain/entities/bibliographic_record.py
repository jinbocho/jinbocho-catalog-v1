from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BibliographicRecord:
	library_id: UUID
	title: str
	main_author: str | None = None
	other_authors: list[str] = field(default_factory=list)
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	language: str | None = None
	genre: str | None = None
	genre_raw: str | None = None
	cover_url: str | None = None
	notes: str | None = None
	incipit: str | None = None
	incipit_source: str | None = None
	incipit_generated_at: datetime | None = None
	id: UUID = field(default_factory=uuid4)
	created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
	updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
