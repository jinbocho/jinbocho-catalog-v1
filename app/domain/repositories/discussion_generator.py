from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DiscussionBookContext:
	title: str
	main_author: str | None = None
	genre: str | None = None
	incipit: str | None = None
	language: str | None = None
	num_questions: int = 3
	# One of "shared", "emerging", "fluent", "teen" (see KID-01).
	reader_age_band: str | None = None
	# The reader's own UI language (from the JWT's language claim), distinct
	# from `language` above (the book's bibliographic language).
	reader_language: str | None = None


class DiscussionQuestionGenerator(ABC):
	@abstractmethod
	async def generate(self, ctx: DiscussionBookContext) -> list[str]:
		"""Never raises — a failed/disabled AI call returns an empty list so the
		caller shows no dinner-table card rather than erroring."""
		...
