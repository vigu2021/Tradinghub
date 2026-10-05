from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tradinghub.auth.models import User
from tradinghub.ledger.crud.accounts import (
    create_account,
    get_account,
    list_accounts_with_balances,
)
from tradinghub.ledger.models import Account, AccountType, Transaction, TransactionKind


async def _account(db_session: AsyncSession, user: User, name: str, unit: str = "GBP") -> Account:
    return await create_account(
        db_session, user_id=user.id, name=name, unit=unit, type=AccountType.CASH
    )


async def _spend(db_session: AsyncSession, account: Account, amount: str) -> None:
    db_session.add(
        Transaction(
            user_id=account.user_id,
            account_id=account.id,
            amount=Decimal(amount),
            kind=TransactionKind.EXPENSE,
            category="rent",
            occurred_at=datetime.now(UTC),
        )
    )
    await db_session.flush()


async def test_an_account_with_no_transactions_has_a_zero_balance(
    db_session: AsyncSession, alice: User
) -> None:
    """COALESCE, not None. The outer join produces a null that SUM cannot turn into a number."""
    await _account(db_session, alice, "Chase")

    balances = await list_accounts_with_balances(db_session, user_id=alice.id)

    assert [row.balance for row in balances] == [Decimal(0)]


async def test_a_balance_is_the_sum_of_its_transactions(
    db_session: AsyncSession, alice: User
) -> None:
    account = await _account(db_session, alice, "Chase")
    await _spend(db_session, account, "-900.50")
    await _spend(db_session, account, "-62.25")

    balances = await list_accounts_with_balances(db_session, user_id=alice.id)

    assert balances[0].balance == Decimal("-962.75")


async def test_every_account_appears_even_when_only_one_has_transactions(
    db_session: AsyncSession, alice: User
) -> None:
    """A plain join would drop the empty account, which is every account on its first day."""
    funded = await _account(db_session, alice, "Chase")
    await _account(db_session, alice, "Cash")
    await _spend(db_session, funded, "-900")

    balances = await list_accounts_with_balances(db_session, user_id=alice.id)

    assert [(row.account.name, row.balance) for row in balances] == [
        ("Cash", Decimal(0)),
        ("Chase", Decimal("-900")),
    ]


async def test_balances_are_ordered_by_name(db_session: AsyncSession, alice: User) -> None:
    for name in ("Zebra", "Apple", "Monzo"):
        await _account(db_session, alice, name)

    balances = await list_accounts_with_balances(db_session, user_id=alice.id)

    assert [row.account.name for row in balances] == ["Apple", "Monzo", "Zebra"]


async def test_one_users_accounts_never_appear_in_anothers_list(
    db_session: AsyncSession, alice: User, bob: User
) -> None:
    await _account(db_session, alice, "Chase")
    await _account(db_session, bob, "Revolut")

    balances = await list_accounts_with_balances(db_session, user_id=alice.id)

    assert [row.account.name for row in balances] == ["Chase"]


async def test_another_users_transactions_never_reach_your_balance(
    db_session: AsyncSession, alice: User, bob: User
) -> None:
    alice_account = await _account(db_session, alice, "Chase")
    bob_account = await _account(db_session, bob, "Revolut")
    await _spend(db_session, alice_account, "-900")
    await _spend(db_session, bob_account, "-5000")

    balances = await list_accounts_with_balances(db_session, user_id=alice.id)

    assert balances[0].balance == Decimal("-900")


async def test_an_account_is_found_by_its_owner(db_session: AsyncSession, alice: User) -> None:
    account = await _account(db_session, alice, "Chase")

    found = await get_account(db_session, account_id=account.id, user_id=alice.id)

    assert found is not None
    assert found.id == account.id


async def test_another_users_account_is_not_found(
    db_session: AsyncSession, alice: User, bob: User
) -> None:
    """The ownership rule. Not a 403: that would confirm the id is real."""
    alice_account = await _account(db_session, alice, "Chase")

    assert await get_account(db_session, account_id=alice_account.id, user_id=bob.id) is None


async def test_a_missing_account_is_not_found(db_session: AsyncSession, alice: User) -> None:
    assert await get_account(db_session, account_id=999_999, user_id=alice.id) is None


async def test_a_created_account_comes_back_with_its_id(
    db_session: AsyncSession, alice: User
) -> None:
    """create_account flushes, so the database has assigned the id before it returns."""
    account = await _account(db_session, alice, "Chase")

    assert account.id is not None
    assert account.created_at is not None


async def test_two_accounts_cannot_share_a_name(db_session: AsyncSession, alice: User) -> None:
    await _account(db_session, alice, "Chase")

    with pytest.raises(IntegrityError):
        await _account(db_session, alice, "Chase")


async def test_a_name_differing_only_in_case_is_a_duplicate(
    db_session: AsyncSession, alice: User
) -> None:
    """name is CITEXT, so the database collides them rather than the application lowercasing."""
    await _account(db_session, alice, "Chase")

    with pytest.raises(IntegrityError):
        await _account(db_session, alice, "chase")


async def test_two_users_may_each_have_an_account_called_chase(
    db_session: AsyncSession, alice: User, bob: User
) -> None:
    await _account(db_session, alice, "Chase")

    assert await _account(db_session, bob, "Chase") is not None


async def test_an_account_may_hold_a_unit_that_is_not_money(
    db_session: AsyncSession, alice: User
) -> None:
    """A holding is an account whose unit is not a currency, which is what a portfolio needs."""
    await create_account(
        db_session, user_id=alice.id, name="Binance BTC", unit="BTC", type=AccountType.CRYPTO
    )

    balances = await list_accounts_with_balances(db_session, user_id=alice.id)

    assert balances[0].account.unit == "BTC"
