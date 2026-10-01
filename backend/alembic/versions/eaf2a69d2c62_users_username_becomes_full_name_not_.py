"""users: username becomes full_name (not unique)

Revision ID: eaf2a69d2c62
Revises: f19fd24435ac
Create Date: 2026-10-01 18:06:33.133455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eaf2a69d2c62'
down_revision: Union[str, Sequence[str], None] = 'f19fd24435ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename (not drop + add), so existing accounts keep their name as their display name.
    # Names don't have to be unique (login is by email), so the unique index goes.
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.alter_column('users', 'username', new_column_name='full_name')


def downgrade() -> None:
    """Downgrade schema."""
    # Note: fails if two users now share the same name (usernames had to be unique).
    op.alter_column('users', 'full_name', new_column_name='username')
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
