"""create fills and positions

Revision ID: 72287cbdfcc1
Revises: 001
Create Date: 2025-09-26 21:42:33.316249

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "72287cbdfcc1"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "fills",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("address", sa.String(64), index=True, nullable=False),
        sa.Column("pair", sa.String(64), index=True, nullable=False),
        sa.Column("is_long", sa.Boolean, nullable=False),
        sa.Column("size", sa.Numeric(38, 18), nullable=False),
        sa.Column("price", sa.Numeric(38, 18), nullable=False),
        sa.Column("notional_usd", sa.Numeric(38, 18), nullable=False),
        sa.Column("fee", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("side", sa.String(16), nullable=False),  # OPEN|CLOSE|...
        sa.Column("maker_taker", sa.String(8), nullable=True),
        sa.Column("block_number", sa.BigInteger, index=True, nullable=False),
        sa.Column("block_hash", sa.String(66), nullable=True),
        sa.Column("tx_hash", sa.String(66), index=True, nullable=False),
        sa.Column("ts", sa.BigInteger, index=True, nullable=False),
        sa.UniqueConstraint(
            "tx_hash", "address", "pair", "side", name="uq_fill_dedupe"
        ),
    )

    op.create_table(
        "positions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("address", sa.String(64), index=True, nullable=False),
        sa.Column("pair", sa.String(64), index=True, nullable=False),
        sa.Column("is_long", sa.Boolean, nullable=False),
        sa.Column("entry_px", sa.Numeric(38, 18), nullable=False),
        sa.Column("size", sa.Numeric(38, 18), nullable=False),
        sa.Column("opened_at", sa.BigInteger, index=True, nullable=False),
        sa.Column("closed_at", sa.BigInteger, index=True, nullable=True),
        sa.Column(
            "pnl_realized", sa.Numeric(38, 18), nullable=False, server_default="0"
        ),
        sa.Column("fees", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("funding", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("tx_open", sa.String(66), nullable=False),
        sa.Column("tx_close", sa.String(66), nullable=True),
        sa.UniqueConstraint(
            "address", "pair", "is_long", "opened_at", name="uq_position_identity"
        ),
    )


def downgrade():
    op.drop_table("positions")
    op.drop_table("fills")
