from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SpineReading:
	title: str
	author: str | None
	position: int


@dataclass
class SpineReadResult:
	"""Outcome of a spine read. ``available`` is True only when the AI actually
	read the photo (``spines`` may still be empty if nothing was legible).
	``reason`` mirrors the AI service's SpineReadStatus so the UI can tell a
	misconfigured model ("unsupported") from a transient failure ("error") or a
	disabled AI module ("disabled")."""

	available: bool
	reason: str  # "ok" | "disabled" | "unsupported" | "error"
	spines: list[SpineReading] = field(default_factory=list)


class ShelfSpineReader(ABC):
	"""Reads book spines from a shelf photo via the AI service (ADR-010)."""

	@abstractmethod
	async def read_spines(self, image_base64: str, media_type: str) -> SpineReadResult: ...
