from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class BookClubQuestionSet:
    """CLUB-08 cached AI-generated discussion prompts, one set per cycle AND
    reader language (get-or-generate, like the Kids DiscussionQuestionSet), so
    the LLM is not repaid on every cycle-page view while still honouring the
    language of whoever asks. Optional: absent AI, no set is ever created and
    the UI shows the section disabled with an upgrade prompt."""

    cycle_id: UUID
    # The reader UI language the prompts were written in (en/it/es/fr), or "" when
    # the language was unknown at generation time. Part of the cache key so each
    # language gets its own stored set.
    language: str = ""
    questions: list[str] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
