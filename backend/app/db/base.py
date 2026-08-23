"""Shared SQLAlchemy declarative base.

Every ORM model (added in a later phase) subclasses `Base` so Alembic's
autogenerate can discover all tables from a single metadata object.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
