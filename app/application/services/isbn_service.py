def normalize_isbn(isbn: str) -> str:
	return isbn.replace("-", "").strip()
