from uuid import uuid4

import pytest

from app.application.use_cases.catalog.book_loans import LendBookUseCase
from app.domain.entities import OwnedBook


@pytest.mark.asyncio
async def test_lend_book_records_borrower_user_id_when_lending_to_a_jinbocho_user(book_repo, book_loan_repo):
	library_id = uuid4()
	book = await book_repo.save(OwnedBook(library_id=library_id, bibliographic_record_id=uuid4()))
	borrower_user_id = uuid4()

	use_case = LendBookUseCase(book_repo, book_loan_repo)
	loan = await use_case.execute(
		book.id, library_id, borrower_name="Jane Smith", borrower_user_id=borrower_user_id,
	)

	assert loan.borrower_user_id == borrower_user_id
	assert loan.borrower_name == "Jane Smith"


@pytest.mark.asyncio
async def test_lend_book_defaults_borrower_user_id_to_none_for_free_text(book_repo, book_loan_repo):
	library_id = uuid4()
	book = await book_repo.save(OwnedBook(library_id=library_id, bibliographic_record_id=uuid4()))

	use_case = LendBookUseCase(book_repo, book_loan_repo)
	loan = await use_case.execute(book.id, library_id, borrower_name="A neighbour")

	assert loan.borrower_user_id is None
