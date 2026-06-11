import pytest

from app.application.use_cases import (
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	ListBibliographicRecordsUseCase,
	ListGenresUseCase,
)
from app.domain.entities import Genre, map_to_genre


@pytest.mark.parametrize(
	"raw, expected",
	[
		(None, None),
		("", None),
		("   ", None),
		("fiction", Genre.FICTION),
		("Fiction", Genre.FICTION),
		("Romanzo", Genre.FICTION),
		("Science Fiction", Genre.SCIENCE_FICTION),
		("Fantascienza", Genre.SCIENCE_FICTION),
		("Giallo", Genre.MYSTERY_THRILLER),
		("Thriller", Genre.MYSTERY_THRILLER),
		("Biografia", Genre.BIOGRAPHY_MEMOIR),
		("Cucina", Genre.COOKING),
		("Fumetto", Genre.COMICS),
		("Storia", Genre.HISTORY),
		("Filosofia", Genre.PHILOSOPHY),
		("science_fiction", Genre.SCIENCE_FICTION),
		("something totally unknown", Genre.OTHER),
	],
)
def test_map_to_genre(raw, expected):
	assert map_to_genre(raw) == expected


@pytest.mark.asyncio
async def test_create_normalizes_genre_and_preserves_raw(record_repo, test_family_id):
	created = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(family_id=test_family_id, title="X", genre="Fantascienza")
	)
	assert created.genre == Genre.SCIENCE_FICTION.value
	assert created.genre_raw == "Fantascienza"


@pytest.mark.asyncio
async def test_filter_and_count_by_genre(record_repo, test_family_id):
	create = CreateBibliographicRecordUseCase(record_repo)
	await create.execute(CreateBibliographicRecordInput(family_id=test_family_id, title="A", genre="Giallo"))
	await create.execute(CreateBibliographicRecordInput(family_id=test_family_id, title="B", genre="Thriller"))
	await create.execute(CreateBibliographicRecordInput(family_id=test_family_id, title="C", genre="Cucina"))

	mystery = await ListBibliographicRecordsUseCase(record_repo).execute(
		test_family_id, q=None, genre=Genre.MYSTERY_THRILLER.value, limit=50, offset=0
	)
	assert len(mystery) == 2

	counts = {gc.genre: gc.count for gc in await ListGenresUseCase(record_repo).execute(test_family_id)}
	assert counts == {Genre.MYSTERY_THRILLER.value: 2, Genre.COOKING.value: 1}
