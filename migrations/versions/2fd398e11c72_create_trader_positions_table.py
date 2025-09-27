"""create trader_positions table

Revision ID: 2fd398e11c72
Revises: 72287cbdfcc1
Create Date: 2025-09-26 21:46:55.746322

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2fd398e11c72'
down_revision = '72287cbdfcc1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "trader_positions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("address", sa.String(64), index=True, nullable=False),
        sa.Column("pair", sa.String(64), index=True, nullable=False),
        sa.Column("is_long", sa.Boolean, nullable=False),
        sa.Column("entry_px", sa.Numeric(38, 18), nullable=False),
        sa.Column("size", sa.Numeric(38, 18), nullable=False),
        sa.Column("opened_at", sa.BigInteger, index=True, nullable=False),
        sa.Column("closed_at", sa.BigInteger, index=True, nullable=True),
        sa.Column("pnl_realized", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("fees", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("funding", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("tx_open", sa.String(66), nullable=False),
        sa.Column("tx_close", sa.String(66), nullable=True),
        sa.UniqueConstraint("address", "pair", "is_long", "opened_at", name="uq_trader_position_identity"),
    )


def downgrade():
    op.drop_table("trader_positions")
