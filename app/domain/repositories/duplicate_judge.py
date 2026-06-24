from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class DuplicateCandidate:
	title: str
	main_author: str | None
	publication_year: int | None


@dataclass
class DuplicateJudgement:
	is_duplicate: bool
	confidence: float
	reason: str


class DuplicateJudge(ABC):
	@abstractmethod
	async def judge(
		self, candidate_a: DuplicateCandidate, candidate_b: DuplicateCandidate
	) -> DuplicateJudgement: ...
