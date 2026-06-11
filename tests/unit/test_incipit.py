import pytest

from app.application.use_cases import (
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	GetOrFetchIncipitUseCase,
	SetIncipitUseCase,
)
from app.domain.entities import IsbnLookupCache
from app.domain.repositories import IsbnLookupCacheRepository
from app.utils import utcnow


class FakeIsbnCacheRepository(IsbnLookupCacheRepository):
	def __init__(self) -> None:
		self.by_isbn: dict[str, IsbnLookupCache] = {}

	async def find_by_isbn(self, isbn: str) -> IsbnLookupCache | None:
		return self.by_isbn.get(isbn)

	async def save(self, entity: IsbnLookupCache) -> IsbnLookupCache:
		self.by_isbn[entity.isbn] = entity
		return entity


@pytest.fixture
def cache_repo():
	return FakeIsbnCacheRepository()


@pytest.mark.asyncio
async def test_incipit_derived_from_isbn_description(record_repo, cache_repo, test_family_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(family_id=test_family_id, title="X", isbn="978000")
	)
	cache_repo.by_isbn["978000"] = IsbnLookupCache(
		isbn="978000", metadata={"notes": "  A gripping opening.  "}, source="google_books", fetched_at=utcnow()
	)

	result = await GetOrFetchIncipitUseCase(record_repo, cache_repo).execute(record.id, test_family_id)
	assert result.text == "A gripping opening."
	assert result.source == "google_books"

	# Second call returns the now-stored value.
	stored = await GetOrFetchIncipitUseCase(record_repo, cache_repo).execute(record.id, test_family_id)
	assert stored.text == "A gripping opening."


@pytest.mark.asyncio
async def test_incipit_absent_without_source(record_repo, cache_repo, test_family_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(family_id=test_family_id, title="No ISBN")
	)
	result = await GetOrFetchIncipitUseCase(record_repo, cache_repo).execute(record.id, test_family_id)
	assert result.text is None
	assert result.source is None


@pytest.mark.asyncio
async def test_set_incipit_manual(record_repo, test_family_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(family_id=test_family_id, title="X")
	)
	result = await SetIncipitUseCase(record_repo).execute(record.id, test_family_id, "  Custom blurb.  ", "manual")
	assert result.text == "Custom blurb."
	assert result.source == "manual"


@pytest.mark.asyncio
async def test_set_incipit_rejects_bad_source(record_repo, test_family_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(family_id=test_family_id, title="X")
	)
	with pytest.raises(ValueError):
		await SetIncipitUseCase(record_repo).execute(record.id, test_family_id, "txt", "bogus")
