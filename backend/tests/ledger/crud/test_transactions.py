from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models import User
from tradinghub.ledger.crud.accounts import create_account
from tradinghub.ledger.crud.transactions import list_transactions
from tradinghub.ledger.models import Account, AccountType, Transaction, TransactionKind
from tradinghub.ledger.schemas.transactions import TransactionFilters

OCTOBER = datetime(2026, 10, 1, tzinfo=UTC)
NOVEMBER = datetime(2026, 11, 1, tzinfo=UTC)


async def _account(db_session: AsyncSession, user: User, name: str = "Chase") -> Account:
    return await create_account(
        db_session, user_id=user.id, name=name, unit="GBP", type=AccountType.CASH
    )


async def _record(
    db_session: AsyncSession,
    account: Account,
    *,
    amount: str = "-10",
    kind: TransactionKind = TransactionKind.EXPENSE,
    category: str | None = "food",
    occurred_at: datetime = OCTOBER,
) -> Transaction:
    transaction = Transaction(
        user_id=account.user_id,
        account_id=account.id,
        amount=Decimal(amount),
        kind=kind,
        category=category,
        occurred_at=occurred_at,
    )
    db_session.add(transaction)
    await db_session.flush()
    return transaction


async def _ids(db_session: AsyncSession, user: User, **filters: object) -> list[int]:
    page, _ = await list_transactions(
        db_session, user_id=user.id, filters=TransactionFilters.model_validate(filters)
    )
    return [transaction.id for transaction in page]


async def test_only_your_own_transactions_are_listed(
    db_session: AsyncSession, alice: User, bob: User
) -> None:
    mine = await _record(db_session, await _account(db_session, alice))
    await _record(db_session, await _account(db_session, bob))

    assert await _ids(db_session, alice) == [mine.id]


async def test_filtering_by_someone_elses_account_finds_nothing(
    db_session: AsyncSession, alice: User, bob: User
) -> None:
    """An empty page, not a 404: nothing about bob's account is confirmed."""
    bobs_account = await _account(db_session, bob)
    await _record(db_session, bobs_account)

    assert await _ids(db_session, alice, account_id=bobs_account.id) == []


async def test_newest_comes_first(db_session: AsyncSession, alice: User) -> None:
    account = await _account(db_session, alice)
    older = await _record(db_session, account, occurred_at=OCTOBER)
    newer = await _record(db_session, account, occurred_at=NOVEMBER)

    assert await _ids(db_session, alice) == [newer.id, older.id]


async def test_paging_through_rows_that_share_a_time_sees_each_once(
    db_session: AsyncSession, alice: User
) -> None:
    """Without id breaking the tie, the order of equal times may change between pages."""
    account = await _account(db_session, alice)
    recorded = [(await _record(db_session, account)).id for _ in range(7)]

    seen: list[int] = []
    for offset in range(0, 8, 2):
        seen += await _ids(db_session, alice, limit=2, offset=offset)

    assert seen == sorted(recorded, reverse=True)


async def test_total_counts_every_match_not_the_page(db_session: AsyncSession, alice: User) -> None:
    account = await _account(db_session, alice)
    for _ in range(5):
        await _record(db_session, account)

    page, total = await list_transactions(
        db_session, user_id=alice.id, filters=TransactionFilters(limit=2)
    )

    assert (len(page), total) == (2, 5)


async def test_total_respects_the_filters(db_session: AsyncSession, alice: User) -> None:
    account = await _account(db_session, alice)
    await _record(db_session, account, kind=TransactionKind.EXPENSE)
    await _record(db_session, account, amount="2000", kind=TransactionKind.INCOME)

    _, total = await list_transactions(
        db_session, user_id=alice.id, filters=TransactionFilters(kind=TransactionKind.INCOME)
    )

    assert total == 1


async def test_filtering_by_account(db_session: AsyncSession, alice: User) -> None:
    chase = await _account(db_session, alice, "Chase")
    monzo = await _account(db_session, alice, "Monzo")
    in_chase = await _record(db_session, chase)
    await _record(db_session, monzo)

    assert await _ids(db_session, alice, account_id=chase.id) == [in_chase.id]


async def test_filtering_by_kind(db_session: AsyncSession, alice: User) -> None:
    account = await _account(db_session, alice)
    await _record(db_session, account, kind=TransactionKind.EXPENSE)
    salary = await _record(db_session, account, amount="2000", kind=TransactionKind.INCOME)

    assert await _ids(db_session, alice, kind="income") == [salary.id]


async def test_filtering_by_category_ignores_its_case(
    db_session: AsyncSession, alice: User
) -> None:
    """Stored categories are lowercase, and the filter is normalised the same way."""
    account = await _account(db_session, alice)
    rent = await _record(db_session, account, category="rent")
    await _record(db_session, account, category="food")

    assert await _ids(db_session, alice, category="Rent") == [rent.id]


async def test_a_date_range_includes_its_start_and_excludes_its_end(
    db_session: AsyncSession, alice: User
) -> None:
    """So October and November, asked for back to back, never both count the midnight row."""
    account = await _account(db_session, alice)
    first_of_october = await _record(db_session, account, occurred_at=OCTOBER)
    await _record(db_session, account, occurred_at=NOVEMBER)
    await _record(db_session, account, occurred_at=datetime(2026, 9, 30, 23, 59, tzinfo=UTC))

    october = await _ids(db_session, alice, occurred_from=OCTOBER, occurred_to=NOVEMBER)

    assert october == [first_of_october.id]


async def test_filters_combine(db_session: AsyncSession, alice: User) -> None:
    chase = await _account(db_session, alice, "Chase")
    monzo = await _account(db_session, alice, "Monzo")
    match = await _record(db_session, chase, category="rent")
    await _record(db_session, chase, category="food")
    await _record(db_session, monzo, category="rent")

    assert await _ids(db_session, alice, account_id=chase.id, category="rent") == [match.id]
