"""Budget factory.

Note BudgetPeriod stores enum NAMES (uppercase) — see
`backend/app/models/budget.py`. The Postgres enum type is `budgetperiod`
with values DAILY/WEEKLY/MONTHLY/QUARTERLY/YEARLY. We hand factory-boy the
enum member (not a string) so SQLAlchemy can serialize correctly via
`values_callable`.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.budget import Budget, BudgetPeriod

from .category import CategoryFactory
from .user import UserFactory


class BudgetFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Budget
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    category = factory.SubFactory(CategoryFactory, user=factory.SelfAttribute("..user"))
    category_id = factory.SelfAttribute("category.id")
    name = factory.Sequence(lambda n: f"Budget {n}")
    amount_cents = 50_000  # $500.00
    period = BudgetPeriod.MONTHLY
    start_date = factory.LazyFunction(lambda: date.today().replace(day=1))
    end_date = None
    alert_threshold = 0.8
    is_active = True
