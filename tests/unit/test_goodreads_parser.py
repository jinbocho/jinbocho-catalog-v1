from datetime import UTC, datetime

import pytest

from app.application.services.goodreads_parser import parse_goodreads_csv
from app.domain.entities import ReadingStatus

_HEADER = (
	"Book Id,Title,Author,Additional Authors,ISBN,ISBN13,My Rating,Average Rating,"
	"Publisher,Year Published,Original Publication Year,Date Read,Bookshelves,"
	"Exclusive Shelf,My Review\n"
)


def _csv(*rows: str) -> str:
	return _HEADER + "\n".join(rows)


def test_rejects_text_without_a_title_column() -> None:
	with pytest.raises(ValueError, match="Title"):
		parse_goodreads_csv("Foo,Bar\n1,2\n")


def test_parses_a_basic_read_row() -> None:
	rows = parse_goodreads_csv(
		_csv(
			'1,Dune,Frank Herbert,,="0441013597",="9780441013593",5,4.25,'
			'Ace,1990,1965,2023/05/12,favorites,read,Loved it'
		)
	)
	assert len(rows) == 1
	row = rows[0]
	assert row.row_number == 1
	assert row.title == "Dune"
	assert row.main_author == "Frank Herbert"
	assert row.isbn == "9780441013593"  # prefers ISBN13 over ISBN
	assert row.publisher == "Ace"
	assert row.publication_year == 1965  # prefers Original Publication Year
	assert row.reading_status == ReadingStatus.READING or row.reading_status == ReadingStatus.READ
	assert row.reading_status == ReadingStatus.READ
	assert row.rating == 5
	assert row.review == "Loved it"
	assert row.read_at == datetime(2023, 5, 12, tzinfo=UTC)
	assert row.tags == ["favorites"]


def test_strips_excel_isbn_escaping() -> None:
	rows = parse_goodreads_csv(_csv('1,Neuromancer,William Gibson,,="0441569560",,0,4.0,,,,,,to-read,'))
	assert rows[0].isbn == "0441569560"


def test_falls_back_to_isbn10_when_isbn13_missing() -> None:
	rows = parse_goodreads_csv(_csv('1,Neuromancer,William Gibson,,="0441569560",,0,4.0,,,,,,to-read,'))
	assert rows[0].isbn == "0441569560"


def test_empty_isbn_columns_yield_none() -> None:
	rows = parse_goodreads_csv(_csv("1,Neuromancer,William Gibson,,,,0,4.0,,,,,,to-read,"))
	assert rows[0].isbn is None


def test_rating_zero_means_unrated() -> None:
	rows = parse_goodreads_csv(_csv("1,Neuromancer,William Gibson,,,,0,4.0,,,,,,to-read,"))
	assert rows[0].rating is None


def test_shelf_mapping_currently_reading() -> None:
	rows = parse_goodreads_csv(_csv("1,Neuromancer,William Gibson,,,,0,4.0,,,,,,currently-reading,"))
	assert rows[0].reading_status == ReadingStatus.READING


def test_unknown_shelf_defaults_to_to_read() -> None:
	rows = parse_goodreads_csv(_csv("1,Neuromancer,William Gibson,,,,0,4.0,,,,,,some-custom-shelf,"))
	assert rows[0].reading_status == ReadingStatus.TO_READ


def test_read_date_only_parsed_for_read_shelf() -> None:
	# Date Read present but shelf is to-read (edge case in real exports) — must not leak a read_at.
	rows = parse_goodreads_csv(_csv("1,Neuromancer,William Gibson,,,,0,4.0,,,,2023/05/12,,to-read,"))
	assert rows[0].read_at is None


def test_malformed_date_read_is_ignored() -> None:
	rows = parse_goodreads_csv(_csv("1,Neuromancer,William Gibson,,,,0,4.0,,,,not-a-date,,read,"))
	assert rows[0].read_at is None


def test_additional_authors_and_bookshelves_are_split_on_comma() -> None:
	row = (
		'1,Good Omens,Terry Pratchett,"Neil Gaiman, Someone Else",,,0,4.0,,,,,'
		'"fantasy, humor, favorites",to-read,'
	)
	rows = parse_goodreads_csv(_csv(row))
	assert rows[0].other_authors == ["Neil Gaiman", "Someone Else"]
	assert rows[0].tags == ["fantasy", "humor", "favorites"]


def test_missing_title_yields_empty_string_not_error() -> None:
	rows = parse_goodreads_csv(_csv(",,William Gibson,,,,0,4.0,,,,,,to-read,"))
	assert rows[0].title == ""


def test_row_numbers_are_stable_and_one_based() -> None:
	rows = parse_goodreads_csv(
		_csv(
			"1,First,A,,,,0,4.0,,,,,,to-read,",
			"2,Second,B,,,,0,4.0,,,,,,to-read,",
		)
	)
	assert [r.row_number for r in rows] == [1, 2]
