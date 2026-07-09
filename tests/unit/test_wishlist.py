from uuid import uuid4

import pytest

from app.application.use_cases import (
	AddToWishlistUseCase,
	CreateBibliographicRecordInput,
	CreateBibliographicRecordUseCase,
	GetWishlistItemUseCase,
)
from app.application.use_cases.catalog.wishlist import AddToWishlistInput


@pytest.mark.asyncio
async def test_get_wishlist_item_returns_item(wishlist_repo, record_repo, test_library_id, test_user_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="Dune")
	)
	added = await AddToWishlistUseCase(wishlist_repo, record_repo).execute(
		AddToWishlistInput(
			library_id=test_library_id,
			user_id=test_user_id,
			bibliographic_record_id=record.id,
		)
	)

	result = await GetWishlistItemUseCase(wishlist_repo).execute(added.id, test_library_id)

	assert result.id == added.id
	assert result.bibliographic_record_id == record.id


@pytest.mark.asyncio
async def test_get_wishlist_item_raises_when_missing(wishlist_repo, test_library_id):
	with pytest.raises(LookupError):
		await GetWishlistItemUseCase(wishlist_repo).execute(uuid4(), test_library_id)


@pytest.mark.asyncio
async def test_get_wishlist_item_raises_for_wrong_library(wishlist_repo, record_repo, test_library_id, test_user_id):
	record = await CreateBibliographicRecordUseCase(record_repo).execute(
		CreateBibliographicRecordInput(library_id=test_library_id, title="Dune")
	)
	added = await AddToWishlistUseCase(wishlist_repo, record_repo).execute(
		AddToWishlistInput(
			library_id=test_library_id,
			user_id=test_user_id,
			bibliographic_record_id=record.id,
		)
	)

	with pytest.raises(LookupError):
		await GetWishlistItemUseCase(wishlist_repo).execute(added.id, uuid4())
