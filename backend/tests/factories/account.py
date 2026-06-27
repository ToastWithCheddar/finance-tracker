"""Account factory.

The `Account` model in the internship code does NOT have `institution_name`
or `last_four` (BE-TEST-001 — that was the bug in `backend/tests/conftest.py`).
We avoid them here.
"""

from __future__ import annotations

from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.account import Account

from .user import UserFactory


class AccountFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Account
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    name = factory.Sequence(lambda n: f"Test Account {n}")
    account_type = "checking"  # checking | savings | credit_card | investment
    balance_cents = 100_000  # $1000.00
    currency = "USD"
    is_active = True
    sync_status = "manual"
    connection_health = "unknown"
    sync_frequency = "manual"
