from app.application.services.isbn_service import expected_language_for_isbn, normalize_isbn


def test_normalize_isbn_strips_hyphens_and_whitespace() -> None:
	assert normalize_isbn(" 978-88-04-12345-6 ") == "9788804123456"


def test_expected_language_for_italian_isbn13_legacy_group() -> None:
	assert expected_language_for_isbn("978-88-04-12345-6") == "it"


def test_expected_language_for_italian_isbn13_new_group() -> None:
	assert expected_language_for_isbn("979-12-345-6789-0") == "it"


def test_expected_language_for_italian_isbn10() -> None:
	assert expected_language_for_isbn("88-04-12345-X") == "it"


def test_expected_language_none_for_other_groups() -> None:
	assert expected_language_for_isbn("978-0-13-468599-1") is None
