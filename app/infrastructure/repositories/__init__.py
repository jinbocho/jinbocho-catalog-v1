from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import BibliographicRecord, BookHistory, Bookcase, IsbnLookupCache, OwnedBook, Room, Section, Shelf
from app.domain.repositories import (
    BibliographicRecordRepository,
    BookHistoryRepository,
    BookcaseRepository,
    IsbnLookupCacheRepository,
    OwnedBookRepository,
    RoomRepository,
    SectionRepository,
    ShelfRepository,
)
from app.infrastructure.models import (
    BibliographicRecordModel,
    BookHistoryModel,
    BookcaseModel,
    IsbnLookupCacheModel,
    OwnedBookModel,
    RoomModel,
    SectionModel,
    ShelfModel,
)


class SQLAlchemyRoomRepository(RoomRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: RoomModel) -> Room:
        return Room(
            id=model.id,
            family_id=model.family_id,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def find_by_id(self, room_id: UUID) -> Optional[Room]:
        model = await self._session.get(RoomModel, room_id)
        return self._to_entity(model) if model else None

    async def find_all_by_family(self, family_id: UUID, limit: int = 50, offset: int = 0) -> list[Room]:
        result = await self._session.execute(
            select(RoomModel).where(RoomModel.family_id == family_id).order_by(RoomModel.name).limit(limit).offset(offset)
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def save(self, room: Room) -> Room:
        model = await self._session.get(RoomModel, room.id)
        if model is None:
            model = RoomModel(
                id=room.id,
                family_id=room.family_id,
                name=room.name,
                description=room.description,
                created_at=room.created_at,
                updated_at=room.updated_at,
            )
            self._session.add(model)
        else:
            model.name = room.name
            model.description = room.description
            model.updated_at = room.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, room_id: UUID) -> None:
        model = await self._session.get(RoomModel, room_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


class SQLAlchemyBookcaseRepository(BookcaseRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookcaseModel) -> Bookcase:
        return Bookcase(
            id=model.id,
            family_id=model.family_id,
            room_id=model.room_id,
            name=model.name,
            description=model.description,
            type=model.type,
            notes=model.notes,
            image_url=model.image_url,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def find_by_id(self, bookcase_id: UUID) -> Optional[Bookcase]:
        model = await self._session.get(BookcaseModel, bookcase_id)
        return self._to_entity(model) if model else None

    async def find_all_by_family(
        self,
        family_id: UUID,
        room_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Bookcase]:
        query = select(BookcaseModel).where(BookcaseModel.family_id == family_id)
        if room_id is not None:
            query = query.where(BookcaseModel.room_id == room_id)
        result = await self._session.execute(query.order_by(BookcaseModel.name).limit(limit).offset(offset))
        return [self._to_entity(model) for model in result.scalars().all()]

    async def save(self, bookcase: Bookcase) -> Bookcase:
        model = await self._session.get(BookcaseModel, bookcase.id)
        if model is None:
            model = BookcaseModel(
                id=bookcase.id,
                family_id=bookcase.family_id,
                room_id=bookcase.room_id,
                name=bookcase.name,
                description=bookcase.description,
                type=bookcase.type,
                notes=bookcase.notes,
                image_url=bookcase.image_url,
                created_at=bookcase.created_at,
                updated_at=bookcase.updated_at,
            )
            self._session.add(model)
        else:
            model.room_id = bookcase.room_id
            model.name = bookcase.name
            model.description = bookcase.description
            model.type = bookcase.type
            model.notes = bookcase.notes
            model.image_url = bookcase.image_url
            model.updated_at = bookcase.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, bookcase_id: UUID) -> None:
        model = await self._session.get(BookcaseModel, bookcase_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


class SQLAlchemySectionRepository(SectionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: SectionModel) -> Section:
        return Section(
            id=model.id,
            bookcase_id=model.bookcase_id,
            section_index=model.section_index,
            label=model.label,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def find_by_id(self, section_id: UUID) -> Optional[Section]:
        model = await self._session.get(SectionModel, section_id)
        return self._to_entity(model) if model else None

    async def find_all_by_bookcase(self, bookcase_id: UUID, limit: int = 50, offset: int = 0) -> list[Section]:
        result = await self._session.execute(
            select(SectionModel)
            .where(SectionModel.bookcase_id == bookcase_id)
            .order_by(SectionModel.section_index)
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def find_all_by_family(
        self,
        family_id: UUID,
        bookcase_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Section]:
        query = select(SectionModel).join(BookcaseModel, SectionModel.bookcase_id == BookcaseModel.id).where(BookcaseModel.family_id == family_id)
        if bookcase_id is not None:
            query = query.where(SectionModel.bookcase_id == bookcase_id)
        result = await self._session.execute(query.order_by(SectionModel.section_index).limit(limit).offset(offset))
        return [self._to_entity(model) for model in result.scalars().all()]

    async def save(self, section: Section) -> Section:
        model = await self._session.get(SectionModel, section.id)
        if model is None:
            model = SectionModel(
                id=section.id,
                bookcase_id=section.bookcase_id,
                section_index=section.section_index,
                label=section.label,
                created_at=section.created_at,
                updated_at=section.updated_at,
            )
            self._session.add(model)
        else:
            model.bookcase_id = section.bookcase_id
            model.section_index = section.section_index
            model.label = section.label
            model.updated_at = section.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, section_id: UUID) -> None:
        model = await self._session.get(SectionModel, section_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


class SQLAlchemyShelfRepository(ShelfRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: ShelfModel) -> Shelf:
        return Shelf(
            id=model.id,
            section_id=model.section_id,
            shelf_index=model.shelf_index,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def find_by_id(self, shelf_id: UUID) -> Optional[Shelf]:
        model = await self._session.get(ShelfModel, shelf_id)
        return self._to_entity(model) if model else None

    async def find_all_by_section(self, section_id: UUID, limit: int = 50, offset: int = 0) -> list[Shelf]:
        result = await self._session.execute(
            select(ShelfModel).where(ShelfModel.section_id == section_id).order_by(ShelfModel.shelf_index).limit(limit).offset(offset)
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def find_all_by_family(
        self,
        family_id: UUID,
        section_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Shelf]:
        query = (
            select(ShelfModel)
            .join(SectionModel, ShelfModel.section_id == SectionModel.id)
            .join(BookcaseModel, SectionModel.bookcase_id == BookcaseModel.id)
            .where(BookcaseModel.family_id == family_id)
        )
        if section_id is not None:
            query = query.where(ShelfModel.section_id == section_id)
        result = await self._session.execute(query.order_by(ShelfModel.shelf_index).limit(limit).offset(offset))
        return [self._to_entity(model) for model in result.scalars().all()]

    async def save(self, shelf: Shelf) -> Shelf:
        model = await self._session.get(ShelfModel, shelf.id)
        if model is None:
            model = ShelfModel(
                id=shelf.id,
                section_id=shelf.section_id,
                shelf_index=shelf.shelf_index,
                notes=shelf.notes,
                created_at=shelf.created_at,
                updated_at=shelf.updated_at,
            )
            self._session.add(model)
        else:
            model.section_id = shelf.section_id
            model.shelf_index = shelf.shelf_index
            model.notes = shelf.notes
            model.updated_at = shelf.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, shelf_id: UUID) -> None:
        model = await self._session.get(ShelfModel, shelf_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


class SQLAlchemyBibliographicRecordRepository(BibliographicRecordRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BibliographicRecordModel) -> BibliographicRecord:
        return BibliographicRecord(
            id=model.id,
            family_id=model.family_id,
            title=model.title,
            main_author=model.main_author,
            other_authors=list(model.other_authors) if model.other_authors else [],
            isbn=model.isbn,
            publisher=model.publisher,
            publication_year=model.publication_year,
            language=model.language,
            genre=model.genre,
            cover_url=model.cover_url,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def find_by_id(self, record_id: UUID) -> Optional[BibliographicRecord]:
        model = await self._session.get(BibliographicRecordModel, record_id)
        return self._to_entity(model) if model else None

    async def find_by_isbn(self, family_id: UUID, isbn: str) -> Optional[BibliographicRecord]:
        result = await self._session.execute(
            select(BibliographicRecordModel).where(
                BibliographicRecordModel.family_id == family_id,
                BibliographicRecordModel.isbn == isbn,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_all_by_family(
        self,
        family_id: UUID,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BibliographicRecord]:
        query = select(BibliographicRecordModel).where(BibliographicRecordModel.family_id == family_id)
        if q:
            ts_vector = func.to_tsvector(
                "simple",
                func.concat(
                    func.coalesce(BibliographicRecordModel.title, ""),
                    " ",
                    func.coalesce(BibliographicRecordModel.main_author, ""),
                    " ",
                    func.coalesce(BibliographicRecordModel.isbn, ""),
                ),
            )
            query = query.where(ts_vector.op("@@")(func.plainto_tsquery("simple", q)))
        result = await self._session.execute(query.order_by(BibliographicRecordModel.created_at.desc()).limit(limit).offset(offset))
        return [self._to_entity(model) for model in result.scalars().all()]

    async def find_all_by_ids(self, record_ids: list[UUID]) -> list[BibliographicRecord]:
        if not record_ids:
            return []
        result = await self._session.execute(
            select(BibliographicRecordModel).where(BibliographicRecordModel.id.in_(record_ids))
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def save(self, record: BibliographicRecord) -> BibliographicRecord:
        model = await self._session.get(BibliographicRecordModel, record.id)
        if model is None:
            model = BibliographicRecordModel(
                id=record.id,
                family_id=record.family_id,
                title=record.title,
                main_author=record.main_author,
                other_authors=record.other_authors or None,
                isbn=record.isbn,
                publisher=record.publisher,
                publication_year=record.publication_year,
                language=record.language,
                genre=record.genre,
                cover_url=record.cover_url,
                notes=record.notes,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
            self._session.add(model)
        else:
            model.title = record.title
            model.main_author = record.main_author
            model.other_authors = record.other_authors or None
            model.isbn = record.isbn
            model.publisher = record.publisher
            model.publication_year = record.publication_year
            model.language = record.language
            model.genre = record.genre
            model.cover_url = record.cover_url
            model.notes = record.notes
            model.updated_at = record.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, record_id: UUID) -> None:
        model = await self._session.get(BibliographicRecordModel, record_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


class SQLAlchemyOwnedBookRepository(OwnedBookRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: OwnedBookModel) -> OwnedBook:
        return OwnedBook(
            id=model.id,
            family_id=model.family_id,
            bibliographic_record_id=model.bibliographic_record_id,
            room_id=model.room_id,
            bookcase_id=model.bookcase_id,
            section_id=model.section_id,
            shelf_id=model.shelf_id,
            shelf_position=model.shelf_position,
            position_description=model.position_description,
            condition=model.condition,
            purchase_date=model.purchase_date,
            purchase_price=Decimal(model.purchase_price) if model.purchase_price is not None else None,
            source=model.source,
            reading_status=model.reading_status,
            tags=list(model.tags) if model.tags else [],
            notes=model.notes,
            is_intentional_duplicate=model.is_intentional_duplicate,
            duplicate_notes=model.duplicate_notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def find_by_id(self, book_id: UUID) -> Optional[OwnedBook]:
        model = await self._session.get(OwnedBookModel, book_id)
        return self._to_entity(model) if model else None

    async def find_all_by_family(
        self,
        family_id: UUID,
        shelf_id: Optional[UUID] = None,
        reading_status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OwnedBook]:
        query = select(OwnedBookModel).where(OwnedBookModel.family_id == family_id)
        if shelf_id is not None:
            query = query.where(OwnedBookModel.shelf_id == shelf_id)
        if reading_status is not None:
            query = query.where(OwnedBookModel.reading_status == reading_status)
        if tag is not None:
            query = query.where(OwnedBookModel.tags.contains([tag]))
        result = await self._session.execute(query.order_by(OwnedBookModel.created_at.desc()).limit(limit).offset(offset))
        return [self._to_entity(model) for model in result.scalars().all()]

    async def find_all_by_shelf_ids(self, shelf_ids: list[UUID]) -> list[OwnedBook]:
        if not shelf_ids:
            return []
        result = await self._session.execute(
            select(OwnedBookModel)
            .where(OwnedBookModel.shelf_id.in_(shelf_ids))
            .order_by(OwnedBookModel.shelf_id, OwnedBookModel.shelf_position, OwnedBookModel.created_at.desc())
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def exists_by_bibliographic_record_id(self, record_id: UUID) -> bool:
        result = await self._session.execute(
            select(func.count()).select_from(OwnedBookModel).where(OwnedBookModel.bibliographic_record_id == record_id)
        )
        return bool(result.scalar_one())

    async def save(self, owned_book: OwnedBook) -> OwnedBook:
        model = await self._session.get(OwnedBookModel, owned_book.id)
        if model is None:
            model = OwnedBookModel(
                id=owned_book.id,
                family_id=owned_book.family_id,
                bibliographic_record_id=owned_book.bibliographic_record_id,
                room_id=owned_book.room_id,
                bookcase_id=owned_book.bookcase_id,
                section_id=owned_book.section_id,
                shelf_id=owned_book.shelf_id,
                shelf_position=owned_book.shelf_position,
                position_description=owned_book.position_description,
                condition=owned_book.condition,
                purchase_date=owned_book.purchase_date,
                purchase_price=owned_book.purchase_price,
                source=owned_book.source,
                reading_status=owned_book.reading_status,
                tags=owned_book.tags or None,
                notes=owned_book.notes,
                is_intentional_duplicate=owned_book.is_intentional_duplicate,
                duplicate_notes=owned_book.duplicate_notes,
                created_at=owned_book.created_at,
                updated_at=owned_book.updated_at,
            )
            self._session.add(model)
        else:
            model.bibliographic_record_id = owned_book.bibliographic_record_id
            model.room_id = owned_book.room_id
            model.bookcase_id = owned_book.bookcase_id
            model.section_id = owned_book.section_id
            model.shelf_id = owned_book.shelf_id
            model.shelf_position = owned_book.shelf_position
            model.position_description = owned_book.position_description
            model.condition = owned_book.condition
            model.purchase_date = owned_book.purchase_date
            model.purchase_price = owned_book.purchase_price
            model.source = owned_book.source
            model.reading_status = owned_book.reading_status
            model.tags = owned_book.tags or None
            model.notes = owned_book.notes
            model.is_intentional_duplicate = owned_book.is_intentional_duplicate
            model.duplicate_notes = owned_book.duplicate_notes
            model.updated_at = owned_book.updated_at
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def delete(self, book_id: UUID) -> None:
        model = await self._session.get(OwnedBookModel, book_id)
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()


class SQLAlchemyBookHistoryRepository(BookHistoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: BookHistoryModel) -> BookHistory:
        return BookHistory(
            id=model.id,
            owned_book_id=model.owned_book_id,
            event_type=model.event_type,
            changed_by=model.changed_by,
            old_data=model.old_data,
            new_data=model.new_data,
            created_at=model.created_at,
        )

    async def find_by_book(self, book_id: UUID, limit: int = 50, offset: int = 0) -> list[BookHistory]:
        result = await self._session.execute(
            select(BookHistoryModel)
            .where(BookHistoryModel.owned_book_id == book_id)
            .order_by(BookHistoryModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_entity(model) for model in result.scalars().all()]

    async def save(self, history: BookHistory) -> BookHistory:
        model = BookHistoryModel(
            id=history.id,
            owned_book_id=history.owned_book_id,
            event_type=history.event_type,
            changed_by=history.changed_by,
            old_data=history.old_data,
            new_data=history.new_data,
            created_at=history.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)


class SQLAlchemyIsbnLookupCacheRepository(IsbnLookupCacheRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: IsbnLookupCacheModel) -> IsbnLookupCache:
        return IsbnLookupCache(
            id=model.id,
            isbn=model.isbn,
            metadata=model.cache_metadata,
            source=model.source,
            fetched_at=model.fetched_at,
            created_at=model.created_at,
        )

    async def find_by_isbn(self, isbn: str) -> Optional[IsbnLookupCache]:
        result = await self._session.execute(select(IsbnLookupCacheModel).where(IsbnLookupCacheModel.isbn == isbn))
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def save(self, entity: IsbnLookupCache) -> IsbnLookupCache:
        stmt = pg_insert(IsbnLookupCacheModel).values(
            isbn=entity.isbn,
            cache_metadata=entity.metadata,
            source=entity.source,
            fetched_at=entity.fetched_at,
        ).on_conflict_do_update(
            index_elements=["isbn"],
            set_={
                "metadata": entity.metadata,
                "source": entity.source,
                "fetched_at": entity.fetched_at,
            },
        )
        await self._session.execute(stmt)
        result = await self._session.execute(select(IsbnLookupCacheModel).where(IsbnLookupCacheModel.isbn == entity.isbn))
        model = result.scalar_one()
        return self._to_entity(model)
