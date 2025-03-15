"""empty message

Revision ID: 61fd8eb3d64d
Revises:
Create Date: 2025-03-15 19:36:56.405582

"""
from typing import Sequence, Union

from alembic import op # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61fd8eb3d64d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
