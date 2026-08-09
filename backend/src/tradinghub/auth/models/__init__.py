"""Database models for authentication.

Every model module must be imported here. Alembic autogenerate only sees classes that have been
imported, and a model it cannot see is one it will write a migration to drop.
"""

from tradinghub.auth.models.user import User

__all__ = ["User"]
