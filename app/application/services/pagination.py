from collections.abc import Awaitable, Callable

DEFAULT_PAGE_SIZE = 500


async def fetch_all_pages[T](
	fetch_page: Callable[[int, int], Awaitable[list[T]]],
	page_size: int | None = None,
) -> list[T]:
	"""Loops a `find_all_by_library(limit, offset)`-shaped repo method until a
	page comes back shorter than the page size, so callers never silently
	cap out at the first page."""
	if page_size is None:
		page_size = DEFAULT_PAGE_SIZE
	results: list[T] = []
	offset = 0
	while True:
		page = await fetch_page(page_size, offset)
		results.extend(page)
		if len(page) < page_size:
			return results
		offset += page_size
