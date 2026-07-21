import pytest

from app.application.use_cases import CreateBibliographicRecordInput, CreateBibliographicRecordUseCase
from app.application.use_cases.catalog.suggest_tags import SuggestTagsUseCase
from app.domain.repositories import TagSuggester
from app.domain.repositories.tag_suggester import TagSuggestion


class FakeTagSuggester(TagSuggester):
    def __init__(self) -> None:
        self.last_reader_language: str | None = None

    async def suggest(
        self,
        title: str,
        main_author: str | None,
        genre: str | None,
        reader_language: str | None = None,
    ) -> TagSuggestion:
        self.last_reader_language = reader_language
        return TagSuggestion(tags=["adventure", "classic"])


@pytest.mark.asyncio
async def test_suggest_tags_passes_reader_language(record_repo, test_library_id):
    """The requester's own UI language must reach the tag suggester — see
    SuggestTagsUseCase.execute."""
    record = await CreateBibliographicRecordUseCase(record_repo).execute(
        CreateBibliographicRecordInput(library_id=test_library_id, title="X")
    )
    tag_suggester = FakeTagSuggester()
    result = await SuggestTagsUseCase(record_repo, tag_suggester).execute(record.id, test_library_id, "fr")
    assert result.tags == ["adventure", "classic"]
    assert tag_suggester.last_reader_language == "fr"
