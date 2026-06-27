"""factory-boy factories for the audit backend test suite.

Each factory is a `SQLAlchemyModelFactory` subclass with
`sqlalchemy_session_persistence = "commit"`. The session is wired up at test
time by `bind_session()` (called from `conftest.py::_bind_factories_to_session`).

Why a registration helper instead of `Meta.sqlalchemy_session = lambda: ...`?
factory-boy resolves `sqlalchemy_session` once at class-construction time. We
need to swap it on every test (because each test gets a fresh SAVEPOINT
session). Setting `_meta.sqlalchemy_session` directly is the supported escape
hatch and avoids subclassing acrobatics.
"""

from __future__ import annotations

from typing import Iterable

from .user import UserFactory
from .account import AccountFactory
from .category import CategoryFactory
from .transaction import TransactionFactory
from .budget import BudgetFactory

_ALL_FACTORIES = (
    UserFactory,
    AccountFactory,
    CategoryFactory,
    TransactionFactory,
    BudgetFactory,
)


def bind_session(session) -> None:
    """Point every factory at the given SQLAlchemy session."""
    for factory in _ALL_FACTORIES:
        factory._meta.sqlalchemy_session = session


def unbind_session() -> None:
    for factory in _ALL_FACTORIES:
        factory._meta.sqlalchemy_session = None


__all__ = [
    "UserFactory",
    "AccountFactory",
    "CategoryFactory",
    "TransactionFactory",
    "BudgetFactory",
    "bind_session",
    "unbind_session",
]
