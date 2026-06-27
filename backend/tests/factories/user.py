"""User factory.

Mirrors `app.models.user.User`. Note: the model has both `display_name` and
separate `first_name`/`last_name` fields; we set both so downstream factories
that rely on either don't see Nones.
"""

from __future__ import annotations

from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from app.models.user import User

_fake = Faker()


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        # session is bound at test time via factories.bind_session
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid4)
    supabase_user_id = factory.LazyFunction(uuid4)
    email = factory.Sequence(lambda n: f"user{n}-{_fake.user_name()}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    display_name = factory.LazyAttribute(lambda o: f"{o.first_name} {o.last_name}")
    avatar_url = None
    locale = "en-US"
    timezone = "UTC"
    currency = "USD"
    is_active = True
    is_verified = True
    notifications_enabled = True
    theme = "light"
    auto_categorization_enabled = True
    default_items_per_page = 25
