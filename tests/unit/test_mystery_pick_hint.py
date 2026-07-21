from uuid import uuid4

from app.application.use_cases.kids.mystery_picks import _mask_hint
from app.domain.entities import BibliographicRecord


def _record(**overrides) -> BibliographicRecord:
	defaults = dict(
		id=uuid4(),
		library_id=uuid4(),
		title="Charlotte's Web",
		main_author="E. B. White",
		genre="childrens",
		incipit="Where's Papa going with that axe? said Fern to her mother.",
	)
	defaults.update(overrides)
	return BibliographicRecord(**defaults)


def test_masks_title_and_author_from_incipit() -> None:
	record = _record(incipit="A story by E. B. White about Charlotte's Web and a pig named Wilbur.")
	hint = _mask_hint(record)
	assert "E. B. White" not in hint
	assert "Charlotte's Web" not in hint


def test_falls_back_to_genre_hint_when_no_incipit() -> None:
	record = _record(incipit=None, genre="fantasy")
	hint = _mask_hint(record)
	assert "fantasy" in hint
	assert record.title not in hint


def test_truncates_long_incipit_to_teaser_length() -> None:
	record = _record(incipit="Word " * 100)
	hint = _mask_hint(record)
	assert len(hint) <= 224
	assert hint.endswith("...")
