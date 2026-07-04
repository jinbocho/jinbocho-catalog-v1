from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.application.use_cases.retention import PurgeExpiredPersonalDataUseCase
from app.domain.entities import FamilyRole, RemovedMember
from tests.unit.conftest import MockRemovedMemberRepository


@pytest.mark.asyncio
async def test_deletes_removed_members_older_than_cutoff() -> None:
	removed_member_repo = MockRemovedMemberRepository()
	now = datetime.now(UTC)

	old_member = RemovedMember(
		id=uuid4(), family_id=uuid4(), full_name="Old Member", email="old@test.com",
		role=FamilyRole.VIEWER, removed_at=now - timedelta(days=400),
	)
	recent_member = RemovedMember(
		id=uuid4(), family_id=uuid4(), full_name="Recent Member", email="recent@test.com",
		role=FamilyRole.VIEWER, removed_at=now - timedelta(days=10),
	)
	await removed_member_repo.save(old_member)
	await removed_member_repo.save(recent_member)

	use_case = PurgeExpiredPersonalDataUseCase(removed_member_repo)
	result = await use_case.execute(older_than=now - timedelta(days=365))

	assert result.removed_members_deleted == 1
	assert old_member.id not in removed_member_repo.members
	assert recent_member.id in removed_member_repo.members


@pytest.mark.asyncio
async def test_returns_zero_when_nothing_expired() -> None:
	removed_member_repo = MockRemovedMemberRepository()

	use_case = PurgeExpiredPersonalDataUseCase(removed_member_repo)
	result = await use_case.execute(older_than=datetime.now(UTC) - timedelta(days=365))

	assert result.removed_members_deleted == 0
