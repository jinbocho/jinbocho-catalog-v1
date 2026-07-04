import csv
import io
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.application.services.isbn_service import normalize_isbn
from app.domain.entities import ReadingStatus

# Goodreads wraps ISBN columns as ="9780441013593" so spreadsheet apps don't
# drop the leading zero or coerce the value to a number — strip that wrapper
# before normalizing.
_ISBN_ESCAPE_RE = re.compile(r'^="?(?P<value>[^"]*)"?$')

_SHELF_TO_STATUS: dict[str, ReadingStatus] = {
	"read": ReadingStatus.READ,
	"currently-reading": ReadingStatus.READING,
	"to-read": ReadingStatus.TO_READ,
}


@dataclass
class GoodreadsRow:
	# 1-based position in the CSV, echoed back through preview/confirm so the
	# FE can correlate a confirm item to the row the user reviewed.
	row_number: int
	title: str
	main_author: str | None
	other_authors: list[str] = field(default_factory=list)
	isbn: str | None = None
	publisher: str | None = None
	publication_year: int | None = None
	reading_status: ReadingStatus = ReadingStatus.TO_READ
	rating: int | None = None
	review: str | None = None
	read_at: datetime | None = None
	tags: list[str] = field(default_factory=list)


def parse_goodreads_csv(text: str) -> list[GoodreadsRow]:
	reader = csv.DictReader(io.StringIO(text))
	if reader.fieldnames is None or "Title" not in reader.fieldnames:
		raise ValueError("Not a Goodreads export: missing 'Title' column")
	return [_parse_row(row_number, raw) for row_number, raw in enumerate(reader, start=1)]


def _parse_row(row_number: int, raw: dict[str, str | None]) -> GoodreadsRow:
	reading_status = _SHELF_TO_STATUS.get((raw.get("Exclusive Shelf") or "").strip().lower(), ReadingStatus.TO_READ)
	return GoodreadsRow(
		row_number=row_number,
		title=(raw.get("Title") or "").strip(),
		main_author=_clean(raw.get("Author")),
		other_authors=_split_list(raw.get("Additional Authors")),
		isbn=_clean_isbn(raw.get("ISBN13")) or _clean_isbn(raw.get("ISBN")),
		publisher=_clean(raw.get("Publisher")),
		publication_year=_parse_int(raw.get("Original Publication Year")) or _parse_int(raw.get("Year Published")),
		reading_status=reading_status,
		rating=_parse_rating(raw.get("My Rating")),
		review=_clean(raw.get("My Review")),
		read_at=_parse_date(raw.get("Date Read")) if reading_status == ReadingStatus.READ else None,
		tags=_split_list(raw.get("Bookshelves")),
	)


def _clean(value: str | None) -> str | None:
	if value is None:
		return None
	stripped = value.strip()
	return stripped or None


def _split_list(value: str | None) -> list[str]:
	if not value:
		return []
	return [item.strip() for item in value.split(",") if item.strip()]


def _clean_isbn(value: str | None) -> str | None:
	if not value:
		return None
	match = _ISBN_ESCAPE_RE.match(value.strip())
	raw = (match.group("value") if match else value).strip()
	return normalize_isbn(raw) if raw else None


def _parse_int(value: str | None) -> int | None:
	if not value:
		return None
	try:
		return int(value.strip())
	except ValueError:
		return None


def _parse_rating(value: str | None) -> int | None:
	rating = _parse_int(value)
	if rating is None or not 1 <= rating <= 5:
		return None
	return rating


def _parse_date(value: str | None) -> datetime | None:
	if not value:
		return None
	try:
		parsed = datetime.strptime(value.strip(), "%Y/%m/%d")
	except ValueError:
		return None
	return parsed.replace(tzinfo=UTC)
