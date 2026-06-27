"""Category factory."""

from __future__ import annotations

from uuid import uuid4

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.category import Category

from .user import UserFactory


class CategoryFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Category
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    id = factory.LazyFunction(uuid4)
    user = factory.SubFactory(UserFactory)
    user_id = factory.SelfAttribute("user.id")
    name = factory.Sequence(lambda n: f"Category {n}")
    description = "Test category"
    emoji = "🧪"
    color = "#FF6B6B"
    is_system = False
    is_active = True
    sort_order = 0
