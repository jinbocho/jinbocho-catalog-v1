import pytest

from app.application.use_cases import (
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	DeriveIncipitUseCase,
	GetIncipitUseCase,
	SetIncipitUseCase,
)
from app.application.use_cases.catalog.generate_ai_incipit import GenerateAiIncipitUseCase
from app.domain.entities import IsbnLookupCache
from app.domain.repositories import EditorialDescriptionProvider, IsbnLookupCacheRepository
from app.infrastructure.external.ai_incipit_client import AiIncipitClient, AiIncipitResult
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


class FakeEditorialDescriptionProvider(EditorialDescriptionProvider):
	async def fetch(self, isbn: str) -> str | None:
		return None


class FakeAiIncipitClient(AiIncipitClient):
	def __init__(self) -> None:
		self.last_reader_language: str | None = None

	async def generate(
		self,
		title: str,
		main_author: str | None,
		genre: str | None,
		language: str | None,
		publisher: str | None,
		publication_year: int | None,
		editorial_description: str | None,
		reader_language: str | None = None,
	) -> AiIncipitResult:
		self.last_reader_language = reader_language
		return AiIncipitResult(text="A gripping tale.", model="fake-model")


@pytest.mark.asyncio
async def test_incipit_derived_from_isbn_description(record_repo, cache_repo, test_library_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="X", isbn="978000")
	)
	cache_repo.by_isbn["978000"] = IsbnLookupCache(
		isbn="978000", metadata={"notes": "  A gripping opening.  "}, source="google_books", fetched_at=utcnow()
	)

	# DeriveIncipitUseCase finds the cache description and saves it.
	result = await DeriveIncipitUseCase(record_repo, cache_repo).execute(record.id, test_library_id)
	assert result.text == "A gripping opening."
	assert result.source == "google_books"

	# GetIncipitUseCase returns the now-stored value without touching the cache.
	stored = await GetIncipitUseCase(record_repo).execute(record.id, test_library_id)
	assert stored.text == "A gripping opening."


@pytest.mark.asyncio
async def test_incipit_absent_without_source(record_repo, cache_repo, test_library_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="No ISBN")
	)
	result = await DeriveIncipitUseCase(record_repo, cache_repo).execute(record.id, test_library_id)
	assert result.text is None
	assert result.source is None


@pytest.mark.asyncio
async def test_set_incipit_manual(record_repo, test_library_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="X")
	)
	result = await SetIncipitUseCase(record_repo).execute(record.id, test_library_id, "  Custom blurb.  ", "manual")
	assert result.text == "Custom blurb."
	assert result.source == "manual"


@pytest.mark.asyncio
async def test_set_incipit_rejects_bad_source(record_repo, test_library_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="X")
	)
	with pytest.raises(ValueError):
		await SetIncipitUseCase(record_repo).execute(record.id, test_library_id, "txt", "bogus")


@pytest.mark.asyncio
async def test_generate_ai_incipit_passes_reader_language(record_repo, test_library_id):
	"""The requester's own UI language, not the book's bibliographic
	language, must reach the AI client — see GenerateAiIncipitUseCase.execute."""
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="X")
	)
	ai_client = FakeAiIncipitClient()
	result = await GenerateAiIncipitUseCase(record_repo, ai_client, FakeEditorialDescriptionProvider()).execute(
		record.id, test_library_id, "es"
	)
	assert result.text == "A gripping tale."
	assert ai_client.last_reader_language == "es"
