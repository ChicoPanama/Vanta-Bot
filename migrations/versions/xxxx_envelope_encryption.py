"""Envelope encryption migration.

Revision ID: xxxx_envelope_encryption
Revises: 72287cbdfcc1
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "xxxx_envelope_encryption"
down_revision = "72287cbdfcc1"
branch_labels = None
depends_on = None


def upgrade():
    """Add envelope encryption support."""
    # Create wallets table with envelope encryption
    op.create_table(
        "wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("address", sa.String(length=64), nullable=False),
        sa.Column("ciphertext_privkey", sa.LargeBinary(), nullable=False),
        sa.Column("dek_wrapped", sa.LargeBinary(), nullable=False),
        sa.Column(
            "encryption_version",
            sa.String(length=16),
            nullable=False,
            server_default="v2",
        ),
        sa.Column("kms_key_id", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("rotated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for wallets
    op.create_index("ix_wallets_user_id", "wallets", ["user_id"])
    op.create_index("ix_wallets_address", "wallets", ["address"])
    op.create_unique_constraint("uq_wallets_address", "wallets", ["address"])

    # Create sent_transactions table for idempotency
    op.create_table(
        "sent_transactions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("tx_hash", sa.String(length=66), nullable=False),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="PENDING"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for sent_transactions
    op.create_index(
        "ix_sent_transactions_request_id", "sent_transactions", ["request_id"]
    )
    op.create_index("ix_sent_transactions_tx_hash", "sent_transactions", ["tx_hash"])
    op.create_index(
        "ix_sent_transactions_wallet_id", "sent_transactions", ["wallet_id"]
    )
    op.create_unique_constraint(
        "uq_sent_transactions_request_id", "sent_transactions", ["request_id"]
    )

    # Add precision columns to existing tables
    op.add_column(
        "fills",
        sa.Column("size_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )
    op.add_column(
        "fills",
        sa.Column("price_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )
    op.add_column(
        "fills",
        sa.Column(
            "notional_usd_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )
    op.add_column(
        "fills",
        sa.Column("fee_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )

    op.add_column(
        "trading_positions",
        sa.Column(
            "entry_px_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )
    op.add_column(
        "trading_positions",
        sa.Column("size_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )
    op.add_column(
        "trading_positions",
        sa.Column(
            "pnl_realized_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )
    op.add_column(
        "trading_positions",
        sa.Column("fees_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )
    op.add_column(
        "trading_positions",
        sa.Column("funding_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )

    op.add_column(
        "copy_configurations",
        sa.Column(
            "sizing_value_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )
    op.add_column(
        "copy_configurations",
        sa.Column(
            "max_leverage_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )
    op.add_column(
        "copy_configurations",
        sa.Column(
            "notional_cap_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )

    op.add_column(
        "copy_positions",
        sa.Column("size_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )
    op.add_column(
        "copy_positions",
        sa.Column(
            "entry_price_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )
    op.add_column(
        "copy_positions",
        sa.Column(
            "copy_ratio_precise", sa.Numeric(precision=38, scale=18), nullable=True
        ),
    )
    op.add_column(
        "copy_positions",
        sa.Column("pnl_precise", sa.Numeric(precision=38, scale=18), nullable=True),
    )

    # Add hot path indexes
    op.create_index("idx_positions_user_status", "positions", ["user_id", "status"])
    op.create_index("idx_copy_events_leader_ts", "copy_events", ["leader_id", "ts"])
    op.create_index("idx_fills_address_ts", "fills", ["address", "ts"])
    op.create_index("idx_fills_pair_ts", "fills", ["pair", "ts"])
    op.create_index("idx_fills_address_pair_ts", "fills", ["address", "pair", "ts"])
    op.create_index(
        "idx_trading_positions_address_opened",
        "trading_positions",
        ["address", "opened_at"],
    )
    op.create_index(
        "idx_trading_positions_address_closed",
        "trading_positions",
        ["address", "closed_at"],
    )
    op.create_index(
        "idx_copy_positions_user_leader",
        "copy_positions",
        ["user_id", "leader_address"],
    )
    op.create_index(
        "idx_copy_positions_user_status", "copy_positions", ["user_id", "status"]
    )

    # Add unique constraints for idempotency
    op.create_unique_constraint("uq_signals_source_ts", "signals", ["source_id", "ts"])


def downgrade():
    """Remove envelope encryption support."""
    # Drop new tables
    op.drop_table("sent_transactions")
    op.drop_table("wallets")

    # Drop precision columns
    op.drop_column("copy_positions", "pnl_precise")
    op.drop_column("copy_positions", "copy_ratio_precise")
    op.drop_column("copy_positions", "entry_price_precise")
    op.drop_column("copy_positions", "size_precise")

    op.drop_column("copy_configurations", "notional_cap_precise")
    op.drop_column("copy_configurations", "max_leverage_precise")
    op.drop_column("copy_configurations", "sizing_value_precise")

    op.drop_column("trading_positions", "funding_precise")
    op.drop_column("trading_positions", "fees_precise")
    op.drop_column("trading_positions", "pnl_realized_precise")
    op.drop_column("trading_positions", "size_precise")
    op.drop_column("trading_positions", "entry_px_precise")

    op.drop_column("fills", "fee_precise")
    op.drop_column("fills", "notional_usd_precise")
    op.drop_column("fills", "price_precise")
    op.drop_column("fills", "size_precise")

    # Drop indexes
    op.drop_constraint("uq_signals_source_ts", "signals", type_="unique")
    op.drop_index("idx_copy_positions_user_status", "copy_positions")
    op.drop_index("idx_copy_positions_user_leader", "copy_positions")
    op.drop_index("idx_trading_positions_address_closed", "trading_positions")
    op.drop_index("idx_trading_positions_address_opened", "trading_positions")
    op.drop_index("idx_fills_address_pair_ts", "fills")
    op.drop_index("idx_fills_pair_ts", "fills")
    op.drop_index("idx_fills_address_ts", "fills")
    op.drop_index("idx_copy_events_leader_ts", "copy_events")
    op.drop_index("idx_positions_user_status", "positions")
