"""user fields

Revision ID: 9af55a00112f
Revises: 96b147d19892
Create Date: 2025-01-07 21:05:17.786759

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9af55a00112f"
down_revision: Union[str, None] = "96b147d19892"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the enum type first
    user_type_enum = sa.Enum(
        "WEB_DESIGNER", "LEARNING_TO_CODE", "EXPERT_DEVELOPER", name="usertype"
    )
    user_type_enum.create(op.get_bind())

    # Add columns with default values
    op.add_column(
        "users",
        sa.Column(
            "user_type", user_type_enum, nullable=False, server_default="WEB_DESIGNER"
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "email_verified", sa.Boolean(), nullable=False, server_default="false"
        ),
    )


def downgrade() -> None:
    # Drop columns first
    op.drop_column("users", "email_verified")
    op.drop_column("users", "user_type")

    # Drop the enum type
    user_type_enum = sa.Enum(name="usertype")
    user_type_enum.drop(op.get_bind())
