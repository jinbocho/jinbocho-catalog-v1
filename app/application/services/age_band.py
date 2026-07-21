from datetime import UTC, datetime

# Mirrors jinbocho-fe/src/features/kids/ageBand.ts — keep both in sync.
# Year only, not full date of birth (GDPR data minimization, see KID-01 in
# jinbocho-docs/backlog/BACKLOG_KIDS_READING_EDUCATION.md).
_BAND_MAX_AGE = (
    ("shared", 5),
    ("emerging", 8),
    ("fluent", 12),
)
_OLDEST_BAND = "teen"


def age_band_for_birth_year(birth_year: int | None, today: datetime | None = None) -> str | None:
    """Returns None when birth_year is unset — callers must treat that as
    band-agnostic, never assume a default band."""
    if birth_year is None:
        return None
    current_year = (today or datetime.now(UTC)).year
    age = current_year - birth_year
    for band, max_age in _BAND_MAX_AGE:
        if age <= max_age:
            return band
    return _OLDEST_BAND
