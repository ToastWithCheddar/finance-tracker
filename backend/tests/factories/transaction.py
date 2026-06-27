"""Transaction factory.

`status` is a free-form String(20) on the model, but the schema layer enums to
lowercase ("pending"/"posted"/"cancelled"). We use lowercase here to match
both the API contract and what `TransactionService` writes back.

`tags` is a Postgres ARRAY(String); we pass a real list, not None, so any
test that does `tags @> ARRAY['x']` can run on the populated row.
"""

from __future__ import annotations

from datetime import date, timezone
from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.transaction import Transaction

from .account import AccountFactory
from .category import CategoryFactory
from .user import UserFactory


class TransactionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Transaction
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    account = factory.SubFactory(AccountFactory, user=factory.SelfAttribute("..user"))
    account_id = factory.SelfAttribute("account.id")
    category = factory.SubFactory(CategoryFactory, user=factory.SelfAttribute("..user"))
    category_id = factory.SelfAttribute("category.id")
    amount_cents = -2_500  # negative = expense
    currency = "USD"
    description = factory.Faker("sentence", nb_words=4)
    merchant = factory.Faker("company")
    transaction_date = factory.LazyFunction(lambda: date.today())
    status = "posted"
    is_transfer = False
    is_hidden = False
    tags = factory.LazyFunction(lambda: ["test"])
    metadata_json = factory.LazyFunction(dict)
