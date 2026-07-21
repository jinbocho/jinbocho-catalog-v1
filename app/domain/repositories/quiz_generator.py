from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class QuizBookContext:
	title: str
	main_author: str | None = None
	genre: str | None = None
	incipit: str | None = None
	language: str | None = None
	num_questions: int = 5
	# Free text the reader supplies — may be a plot summary, "I'm up to
	# chapter 3", or what to focus on. See ai-service's GenerateQuizUseCase:
	# the model may treat facts stated here as real (that's the intended way
	# to get plot-aware questions despite no full book text being stored).
	extra_context: str | None = None
	# One of "shared", "emerging", "fluent", "teen" (see KID-01) — calibrates
	# question wording/difficulty. Kept separate from extra_context so
	# supplying it never triggers GenerateQuizQuestionsUseCase's "always
	# regenerate" bypass, which extra_context alone still does.
	reader_age_band: str | None = None
	# The reader's own UI language (from the JWT's language claim), distinct
	# from `language` above (the book's bibliographic language) — the output
	# must follow the reader, not the book. See jinbocho-docs backlog on AI
	# content language.
	reader_language: str | None = None


@dataclass
class GeneratedQuizQuestion:
	prompt: str
	choices: list[str] = field(default_factory=list)
	correct_index: int = 0


class QuizGenerator(ABC):
	@abstractmethod
	async def generate(self, ctx: QuizBookContext) -> list[GeneratedQuizQuestion]:
		"""Never raises — a failed/disabled AI call returns an empty list so the
		caller falls back to manually-authored questions."""
		...
