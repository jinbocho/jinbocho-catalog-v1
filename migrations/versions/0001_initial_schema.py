"""Initial schema: rooms, bookcases, sections, shelves, bibliographic_records,
owned_books, book_history, isbn_lookup_cache

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # ENUM types
    # -----------------------------------------------------------------------
    reading_status = postgresql.ENUM(
        "to_read", "reading", "read", name="reading_status", create_type=False
    )
    book_condition = postgresql.ENUM(
        "new", "good", "fair", "poor", name="book_condition", create_type=False
    )
    book_source = postgresql.ENUM(
        "purchased", "gift", "borrowed", "other", name="book_source", create_type=False
    )
    book_event_type = postgresql.ENUM(
        "created",
        "metadata_updated",
        "position_changed",
        "reading_status_changed",
        "deleted",
        name="book_event_type",
        create_type=False,
    )

    op.execute("CREATE TYPE reading_status AS ENUM ('to_read', 'reading', 'read')")
    op.execute("CREATE TYPE book_condition AS ENUM ('new', 'good', 'fair', 'poor')")
    op.execute("CREATE TYPE book_source AS ENUM ('purchased', 'gift', 'borrowed', 'other')")
    op.execute(
        "CREATE TYPE book_event_type AS ENUM "
        "('created', 'metadata_updated', 'position_changed', 'reading_status_changed', 'deleted')"
    )

    # -----------------------------------------------------------------------
    # rooms
    # -----------------------------------------------------------------------
    op.create_table(
        "rooms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_rooms_family_id", "rooms", ["family_id"])

    # -----------------------------------------------------------------------
    # bookcases
    # -----------------------------------------------------------------------
    op.create_table(
        "bookcases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "room_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rooms.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("type", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("image_url", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_bookcases_family_id", "bookcases", ["family_id"])
    op.create_index("ix_bookcases_room_id", "bookcases", ["room_id"])

    # -----------------------------------------------------------------------
    # sections
    # -----------------------------------------------------------------------
    op.create_table(
        "sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bookcase_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bookcases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_index", sa.Integer, nullable=False),
        sa.Column("label", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("bookcase_id", "section_index", name="uq_sections_bookcase_index"),
    )
    op.create_index("ix_sections_bookcase_id", "sections", ["bookcase_id"])

    # -----------------------------------------------------------------------
    # shelves
    # -----------------------------------------------------------------------
    op.create_table(
        "shelves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "section_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("shelf_index", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("section_id", "shelf_index", name="uq_shelves_section_index"),
    )
    op.create_index("ix_shelves_section_id", "shelves", ["section_id"])

    # -----------------------------------------------------------------------
    # bibliographic_records
    # -----------------------------------------------------------------------
    op.create_table(
        "bibliographic_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("main_author", sa.String(255)),
        sa.Column("other_authors", postgresql.ARRAY(sa.String)),
        sa.Column("isbn", sa.String(20)),
        sa.Column("publisher", sa.String(255)),
        sa.Column("publication_year", sa.Integer),
        sa.Column("language", sa.String(10)),
        sa.Column("genre", sa.String(100)),
        sa.Column("cover_url", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_bibliographic_records_family_id", "bibliographic_records", ["family_id"])
    op.create_index("ix_bibliographic_records_isbn", "bibliographic_records", ["isbn"])

    # -----------------------------------------------------------------------
    # owned_books
    # -----------------------------------------------------------------------
    op.create_table(
        "owned_books",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "bibliographic_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bibliographic_records.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rooms.id", ondelete="SET NULL")),
        sa.Column("bookcase_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bookcases.id", ondelete="SET NULL")),
        sa.Column("section_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sections.id", ondelete="SET NULL")),
        sa.Column("shelf_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("shelves.id", ondelete="SET NULL")),
        sa.Column("shelf_position", sa.Integer),
        sa.Column("position_description", sa.Text),
        sa.Column("condition", postgresql.ENUM("new", "good", "fair", "poor", name="book_condition", create_type=False)),
        sa.Column("purchase_date", sa.Date),
        sa.Column("purchase_price", sa.Numeric(10, 2)),
        sa.Column("source", postgresql.ENUM("purchased", "gift", "borrowed", "other", name="book_source", create_type=False)),
        sa.Column(
            "reading_status",
            postgresql.ENUM("to_read", "reading", "read", name="reading_status", create_type=False),
            nullable=False,
            server_default="to_read",
        ),
        sa.Column("tags", postgresql.ARRAY(sa.String)),
        sa.Column("notes", sa.Text),
        sa.Column("is_intentional_duplicate", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("duplicate_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_owned_books_family_id", "owned_books", ["family_id"])
    op.create_index("ix_owned_books_bibliographic_record_id", "owned_books", ["bibliographic_record_id"])
    op.create_index("ix_owned_books_shelf_id", "owned_books", ["shelf_id"])
    op.create_index("ix_owned_books_reading_status", "owned_books", ["reading_status"])

    # -----------------------------------------------------------------------
    # book_history
    # -----------------------------------------------------------------------
    op.create_table(
        "book_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owned_book_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "event_type",
            postgresql.ENUM(
                "created",
                "metadata_updated",
                "position_changed",
                "reading_status_changed",
                "deleted",
                name="book_event_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("old_data", postgresql.JSONB),
        sa.Column("new_data", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_book_history_owned_book_id", "book_history", ["owned_book_id"])

    # -----------------------------------------------------------------------
    # isbn_lookup_cache
    # -----------------------------------------------------------------------
    op.create_table(
        "isbn_lookup_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("isbn", sa.String(20), nullable=False, unique=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("ix_isbn_lookup_cache_isbn", "isbn_lookup_cache", ["isbn"])


def downgrade() -> None:
    op.drop_table("isbn_lookup_cache")
    op.drop_table("book_history")
    op.drop_table("owned_books")
    op.drop_table("bibliographic_records")
    op.drop_table("shelves")
    op.drop_table("sections")
    op.drop_table("bookcases")
    op.drop_table("rooms")

    op.execute("DROP TYPE IF EXISTS book_event_type")
    op.execute("DROP TYPE IF EXISTS book_source")
    op.execute("DROP TYPE IF EXISTS book_condition")
    op.execute("DROP TYPE IF EXISTS reading_status")
