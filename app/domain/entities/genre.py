from enum import StrEnum


class Genre(StrEnum):
	FICTION = "fiction"
	FANTASY = "fantasy"
	SCIENCE_FICTION = "science_fiction"
	MYSTERY_THRILLER = "mystery_thriller"
	ROMANCE = "romance"
	HORROR = "horror"
	HISTORICAL = "historical"
	BIOGRAPHY_MEMOIR = "biography_memoir"
	HISTORY = "history"
	SCIENCE = "science"
	PHILOSOPHY = "philosophy"
	RELIGION = "religion"
	SELF_HELP = "self_help"
	BUSINESS = "business"
	ART = "art"
	POETRY = "poetry"
	DRAMA = "drama"
	COMICS = "comics"
	CHILDREN = "children"
	YOUNG_ADULT = "young_adult"
	TRAVEL = "travel"
	COOKING = "cooking"
	ESSAY = "essay"
	REFERENCE = "reference"
	OTHER = "other"


# Substring keywords (multilingual: en/it/es/fr) mapped to a normalized genre.
# Order matters: more specific buckets are checked before broader ones
# (e.g. "science fiction" before "science", "historical" before "history").
_KEYWORDS: list[tuple[Genre, tuple[str, ...]]] = [
	(Genre.SCIENCE_FICTION, ("science fiction", "sci-fi", "scifi", "fantascienza", "ciencia ficcion", "ciencia ficción")),
	(Genre.YOUNG_ADULT, ("young adult", "adolescen", "teen", "ya ")),
	(Genre.MYSTERY_THRILLER, ("mystery", "thriller", "crime", "detective", "giallo", "noir", "suspense", "polar", "policiaco", "policíaco")),
	(Genre.BIOGRAPHY_MEMOIR, ("biograph", "biografi", "memoir", "autobiograf", "memorias")),
	(Genre.HISTORICAL, ("historical fiction", "historical novel", "romanzo storico", "novela historica", "novela histórica")),
	(Genre.SELF_HELP, ("self-help", "self help", "auto-aiuto", "psycholog", "psicolog", "wellness", "benessere", "autoayuda", "developpement personnel", "développement personnel")),
	(Genre.COMICS, ("comic", "graphic novel", "fumetto", "manga", "bande dessinee", "bande dessinée", "historieta", "tebeo")),
	(Genre.FANTASY, ("fantasy", "fantastico", "fantastique", "fantastica", "fantástica")),
	(Genre.ROMANCE, ("romance", "romantic", "rosa", "romanc")),
	(Genre.HORROR, ("horror", "terror", "terrore")),
	(Genre.SCIENCE, ("science", "scienza", "scien", "physics", "fisica", "física", "biolog", "mathematic", "matematic", "technolog", "tecnolog", "computer", "informatic")),
	(Genre.HISTORY, ("history", "storia", "histoire", "historia", "storico", "histor")),
	(Genre.PHILOSOPHY, ("philosoph", "filosof")),
	(Genre.RELIGION, ("religion", "religione", "religios", "spiritual", "theolog", "teolog")),
	(Genre.BUSINESS, ("business", "economic", "economia", "finance", "finanza", "management", "marketing", "negocios", "économie", "economie")),
	(Genre.ART, ("art", "arte", "music", "musica", "música", "photograph", "fotograf", "design", "cinema", "film")),
	(Genre.POETRY, ("poetry", "poesia", "poesía", "poesie", "poésie", "poem")),
	(Genre.DRAMA, ("drama", "teatro", "theatre", "theater", "théâtre", "play")),
	(Genre.CHILDREN, ("children", "juvenile", "bambini", "kids", "picture book", "infantil", "enfant", "ragazzi")),
	(Genre.TRAVEL, ("travel", "viaggi", "voyage", "viajes", "guide", "guida")),
	(Genre.COOKING, ("cook", "cucina", "cuisine", "cocina", "food", "recipe", "ricett", "recett", "gastronom")),
	(Genre.ESSAY, ("essay", "saggio", "saggistica", "ensayo", "essai")),
	(Genre.REFERENCE, ("reference", "dictionary", "dizionario", "encyclopedi", "enciclopedi", "manual", "manuale", "textbook", "diccionario")),
	(Genre.FICTION, ("fiction", "novel", "romanzo", "narrativa", "literary", "literatura", "roman", "novela")),
]

_BY_VALUE = {genre.value: genre for genre in Genre}


def map_to_genre(raw: str | None) -> Genre | None:
	"""Normalize a free-text or external (Google Books / Open Library) genre to a Genre.

	Returns None for empty input so callers can leave the field unset; falls back to
	Genre.OTHER when text is present but matches no known bucket.
	"""
	if raw is None:
		return None
	text = raw.strip().lower()
	if not text:
		return None
	if text in _BY_VALUE:
		return _BY_VALUE[text]
	for genre, keywords in _KEYWORDS:
		for keyword in keywords:
			if keyword and keyword in text:
				return genre
	return Genre.OTHER
