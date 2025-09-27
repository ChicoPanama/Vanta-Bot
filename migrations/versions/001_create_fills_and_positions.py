# migrations/versions/001_create_fills_and_positions.py
"""create fills and positions

Revision ID: 001
Revises: 
Create Date: 2025-01-26 21:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create fills table
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
    )

    # Create positions table
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
        sa.Column("pnl_realized", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("fees", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("funding", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("tx_open", sa.String(66), nullable=False),
        sa.Column("tx_close", sa.String(66), nullable=True),
    )

    # Create copy_configurations table
    op.create_table(
        "copy_configurations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, index=True, nullable=False),
        sa.Column("leader_address", sa.String(64), index=True, nullable=False),
        sa.Column("sizing_mode", sa.String(32), nullable=False),  # "FIXED_NOTIONAL" or "PCT_EQUITY"
        sa.Column("sizing_value", sa.Numeric(38, 18), nullable=False),
        sa.Column("max_slippage_bps", sa.BigInteger, nullable=False),
        sa.Column("max_leverage", sa.Numeric(38, 18), nullable=False),
        sa.Column("notional_cap", sa.Numeric(38, 18), nullable=False),
        sa.Column("pair_filters", sa.String(512), nullable=True),  # JSON
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.BigInteger, index=True, nullable=False),
        sa.Column("updated_at", sa.BigInteger, index=True, nullable=False),
    )

    # Create copy_positions table
    op.create_table(
        "copy_positions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger, index=True, nullable=False),
        sa.Column("leader_address", sa.String(64), index=True, nullable=False),
        sa.Column("leader_tx_hash", sa.String(66), index=True, nullable=False),
        sa.Column("copy_tx_hash", sa.String(66), index=True, nullable=False),
        sa.Column("pair", sa.String(64), nullable=False),
        sa.Column("is_long", sa.Boolean, nullable=False),
        sa.Column("size", sa.Numeric(38, 18), nullable=False),
        sa.Column("entry_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("copy_ratio", sa.Numeric(38, 18), nullable=False),
        sa.Column("opened_at", sa.BigInteger, index=True, nullable=False),
        sa.Column("closed_at", sa.BigInteger, index=True, nullable=True),
        sa.Column("pnl", sa.Numeric(38, 18), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False),  # "OPEN", "CLOSED", "LIQUIDATED"
    )

    # Create composite indexes for efficient queries
    op.create_index('idx_fills_address_ts', 'fills', ['address', 'ts'])
    op.create_index('idx_fills_pair_ts', 'fills', ['pair', 'ts'])
    op.create_index('idx_fills_address_pair_ts', 'fills', ['address', 'pair', 'ts'])
    
    op.create_index('idx_positions_address_opened', 'positions', ['address', 'opened_at'])
    op.create_index('idx_positions_address_closed', 'positions', ['address', 'closed_at'])
    
    op.create_index('idx_copy_positions_user_leader', 'copy_positions', ['user_id', 'leader_address'])
    op.create_index('idx_copy_positions_user_status', 'copy_positions', ['user_id', 'status'])

    # Create unique constraints
    op.create_unique_constraint('uq_fill_dedupe', 'fills', ['tx_hash', 'address', 'pair', 'side'])
    op.create_unique_constraint('uq_position_identity', 'positions', ['address', 'pair', 'is_long', 'opened_at'])
    op.create_unique_constraint('uq_copy_config_user_leader', 'copy_configurations', ['user_id', 'leader_address'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_copy_positions_user_status', 'copy_positions')
    op.drop_index('idx_copy_positions_user_leader', 'copy_positions')
    op.drop_index('idx_positions_address_closed', 'positions')
    op.drop_index('idx_positions_address_opened', 'positions')
    op.drop_index('idx_fills_address_pair_ts', 'fills')
    op.drop_index('idx_fills_pair_ts', 'fills')
    op.drop_index('idx_fills_address_ts', 'fills')
    
    # Drop tables
    op.drop_table("copy_positions")
    op.drop_table("copy_configurations")
    op.drop_table("positions")
    op.drop_table("fills")
