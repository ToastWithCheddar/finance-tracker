from __future__ import annotations

from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, func, event
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all models."""
    pass


class BaseModel(Base):
    __abstract__ = True

    # Primary key and timestamps
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),  # server-side update on write
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"

    def to_dict(self) -> dict[str, Any]:
        """Convert model to a plain dict of column -> value."""
        # NOTE: this is not JSON-safe; for JSON serialization you may need to
        # isoformat datetimes, etc.
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


# Optional: also update timestamp on the Python side before UPDATE.
# Not strictly needed because 'onupdate=func.now()' handles it server-side,
# but harmless if you want both.
#@event.listens_for(BaseModel, "before_update", propagate=True)
#def timestamp_before_update(mapper, connection, target) -> None:
#    target.updated_at = datetime.now(timezone.utc)
