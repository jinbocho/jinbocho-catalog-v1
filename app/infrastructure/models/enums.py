from sqlalchemy import Enum

reading_status_enum = Enum("to_read", "reading", "read", name="reading_status")
book_condition_enum = Enum("new", "good", "fair", "poor", name="book_condition")
book_source_enum = Enum("purchased", "gift", "borrowed", "other", name="book_source")
book_event_type_enum = Enum(
	"created",
	"metadata_updated",
	"position_changed",
	"reading_status_changed",
	"deleted",
	name="book_event_type",
)
