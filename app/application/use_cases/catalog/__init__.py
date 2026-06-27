from .add_book import AddBookInput, AddBookUseCase, FuzzyDedupConfig
from app.domain.errors import DuplicateBookConflict, DuplicateBookError
from .book_loans import (
	LendBookUseCase,
	ListActiveFamilyLoansUseCase,
	ListAllFamilyLoansUseCase,
	ListBookLoansUseCase,
	ReturnBookUseCase,
)
from .book_reads import ListBookReadsUseCase, ListFamilyReadsUseCase, MarkBookReadUseCase, UnmarkBookReadUseCase
from .create_bibliographic_record import CreateBibliographicRecordInput, CreateBibliographicRecordUseCase
from .delete_bibliographic_record import DeleteBibliographicRecordUseCase
from .delete_book import DeleteBookInput, DeleteBookUseCase
from .get_bibliographic_record import GetBibliographicRecordUseCase
from .get_book_history import GetBookHistoryUseCase
from .get_or_fetch_incipit import DeriveIncipitUseCase, GetIncipitUseCase, IncipitOutput
from .get_owned_book import GetOwnedBookOutput, GetOwnedBookUseCase
from .list_bibliographic_records import ListBibliographicRecordsUseCase
from .list_genres import GenreCount, ListGenresUseCase
from .list_owned_books import ListOwnedBooksUseCase
from .loan_reminders import SendLoanRemindersUseCase
from .set_incipit import SetIncipitUseCase
from .update_bibliographic_record import UpdateBibliographicRecordInput, UpdateBibliographicRecordUseCase
from .update_book_metadata import UpdateBookMetadataInput, UpdateBookMetadataUseCase
from .update_book_position import UpdateBookPositionInput, UpdateBookPositionUseCase
from .update_reading_status import UpdateReadingStatusInput, UpdateReadingStatusUseCase
from .wishlist import AddToWishlistUseCase, ListFamilyWishlistUseCase, RemoveFromWishlistUseCase

__all__ = [
	# Add/Delete/Update Books
	"AddBookInput",
	"AddBookUseCase",
	"DuplicateBookConflict",
	"DuplicateBookError",
	"FuzzyDedupConfig",
	# Book loans (external lending)
	"LendBookUseCase",
	"ReturnBookUseCase",
	"ListBookLoansUseCase",
	"ListActiveFamilyLoansUseCase",
	"ListAllFamilyLoansUseCase",
	"SendLoanRemindersUseCase",
	# Book reads (per-member reading history)
	"MarkBookReadUseCase",
	"UnmarkBookReadUseCase",
	"ListBookReadsUseCase",
	"ListFamilyReadsUseCase",
	"DeleteBookInput",
	"DeleteBookUseCase",
	"UpdateBookPositionInput",
	"UpdateBookPositionUseCase",
	"UpdateReadingStatusInput",
	"UpdateReadingStatusUseCase",
	# Bibliographic Records
	"CreateBibliographicRecordInput",
	"CreateBibliographicRecordUseCase",
	"DeleteBibliographicRecordUseCase",
	"GetBibliographicRecordUseCase",
	"ListBibliographicRecordsUseCase",
	"ListGenresUseCase",
	"GenreCount",
	"DeriveIncipitUseCase",
	"GetIncipitUseCase",
	"SetIncipitUseCase",
	"IncipitOutput",
	"UpdateBibliographicRecordInput",
	"UpdateBibliographicRecordUseCase",
	# Owned Books
	"GetBookHistoryUseCase",
	"GetOwnedBookUseCase",
	"GetOwnedBookOutput",
	"ListOwnedBooksUseCase",
	"UpdateBookMetadataInput",
	"UpdateBookMetadataUseCase",
	# Wishlist
	"AddToWishlistUseCase",
	"RemoveFromWishlistUseCase",
	"ListFamilyWishlistUseCase",
]
