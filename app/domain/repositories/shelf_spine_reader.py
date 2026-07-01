from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SpineReading:
	title: str
	author: str | None
	position: int


class ShelfSpineReader(ABC):
	"""Reads book spines from a shelf photo via the AI service (ADR-010).

	None means vision is unavailable (AI module disabled, LLM not configured,
	or the call failed); an empty list means the photo was processed but no
	spine was legible.
	"""

	@abstractmethod
	async def read_spines(self, image_base64: str, media_type: str) -> list[SpineReading] | None: ...
