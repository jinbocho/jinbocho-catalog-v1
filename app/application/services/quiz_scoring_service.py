from dataclasses import dataclass
from uuid import UUID

from app.domain.entities import QuizQuestion

# 70% correct to "pass" — arbitrary but reasonable for a kids' comprehension
# check; not configurable per-library, kept simple for MVP.
_PASS_THRESHOLD = 0.7


@dataclass
class QuizScoreResult:
    score: int
    total: int
    passed: bool


class QuizScoringService:
    """Pure computation, no persistence — the calling use case saves the
    resulting QuizAttempt. Mirrors PositionValidationService's shape."""

    def score(self, questions: list[QuizQuestion], answers: dict[UUID, int]) -> QuizScoreResult:
        total = len(questions)
        correct = sum(1 for q in questions if answers.get(q.id) == q.correct_index)
        passed = total > 0 and (correct / total) >= _PASS_THRESHOLD
        return QuizScoreResult(score=correct, total=total, passed=passed)
