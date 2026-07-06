from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass
class DuplicateBookConflict:
	conflict_type: Literal["isbn_match", "title_author_match", "fuzzy_match"]
	existing_book_id: UUID
	existing_record_id: UUID
	title: str
	main_author: str | None
	isbn: str | None
	# Who already has it and where — the check is library-wide, not owner-scoped
	# (two members can each legitimately own a copy), so the caller needs this
	# to decide whether adding a separate copy makes sense.
	existing_owner_id: UUID | None
	existing_room_id: UUID | None
	existing_bookcase_id: UUID | None
	existing_section_id: UUID | None
	existing_shelf_id: UUID | None
	# Only set for conflict_type="fuzzy_match" when the ambiguous-band LLM
	# judge ran — None for isbn_match/title_author_match (no judgement needed)
	# and for a fuzzy_match confident enough to skip the LLM call entirely.
	match_reason: str | None = None


class DuplicateBookError(Exception):
	"""Raised instead of creating the book when it looks like the caller
	already owns this exact book and hasn't confirmed they want a second copy
	anyway (see AddBookInput.is_intentional_duplicate)."""

	def __init__(self, conflict: DuplicateBookConflict) -> None:
		self.conflict = conflict
		super().__init__(f"Duplicate book detected: {conflict.conflict_type}")
