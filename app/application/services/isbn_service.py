def normalize_isbn(isbn: str) -> str:
	return isbn.replace("-", "").strip()


def expected_language_for_isbn(isbn: str) -> str | None:
	"""Infers the edition language from the ISBN registration group, where unambiguous.

	Only Italian groups are covered: that's the language mismatch this app's users
	actually hit (foreign-language metadata returned for an Italian-printed scan).
	Returns None for every other group rather than guessing, so unmapped ISBNs keep
	today's first-match behaviour.
	"""
	digits = normalize_isbn(isbn)
	if digits.startswith("97888") or digits.startswith("97912"):
		return "it"
	if len(digits) == 10 and digits.startswith("88"):
		return "it"
	return None
