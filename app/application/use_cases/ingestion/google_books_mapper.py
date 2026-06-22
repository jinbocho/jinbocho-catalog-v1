from typing import Any


def extract_year(value: str | None) -> int | None:
	if not value:
		return None
	for part in value.split("-"):
		if part[:4].isdigit():
			return int(part[:4])
	digits = "".join(ch for ch in value if ch.isdigit())
	if len(digits) >= 4:
		return int(digits[:4])
	return None


def volume_to_metadata(volume: dict[str, Any], isbn: str | None = None) -> dict[str, Any]:
	authors = volume.get("authors") or []
	resolved_isbn = isbn or _industry_identifier(volume, "ISBN_13") or _industry_identifier(volume, "ISBN_10")
	return {
		"title": volume.get("title"),
		"main_author": authors[0] if authors else None,
		"other_authors": authors[1:],
		"publisher": volume.get("publisher"),
		"publication_year": extract_year(volume.get("publishedDate")),
		"language": volume.get("language"),
		"genre": (volume.get("categories") or [None])[0],
		"cover_url": (volume.get("imageLinks") or {}).get("thumbnail"),
		"notes": volume.get("description"),
		"isbn": resolved_isbn,
	}


def _industry_identifier(volume: dict[str, Any], identifier_type: str) -> str | None:
	for identifier in volume.get("industryIdentifiers") or []:
		if identifier.get("type") == identifier_type:
			value = identifier.get("identifier")
			return value if isinstance(value, str) else None
	return None
