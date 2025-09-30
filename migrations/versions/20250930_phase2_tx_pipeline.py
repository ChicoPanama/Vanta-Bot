"""Phase 2: Transaction pipeline models.

Revision ID: 20250930_phase2_tx_pipeline
Revises: 20250930_phase1_envelope_crypto
Create Date: 2025-09-30 02:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250930_phase2_tx_pipeline"
down_revision = "20250930_phase1_envelope_crypto"
branch_labels = None
depends_on = None


def upgrade():
    """Add transaction pipeline tables."""
    # Create tx_intents table
    op.create_table(
        "tx_intents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("intent_key", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="CREATED"),
        sa.Column("intent_metadata", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intent_key"),
    )

    with op.batch_alter_table("tx_intents", schema=None) as batch_op:
        batch_op.create_index("ix_txintent_status_created", ["status", "created_at"])
        batch_op.create_index(
            batch_op.f("ix_tx_intents_intent_key"), ["intent_key"], unique=True
        )

    # Create tx_sends table
    op.create_table(
        "tx_sends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("intent_id", sa.Integer(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("nonce", sa.Integer(), nullable=False),
        sa.Column("max_fee_per_gas", sa.BigInteger(), nullable=False),
        sa.Column("max_priority_fee_per_gas", sa.BigInteger(), nullable=False),
        sa.Column("gas_limit", sa.BigInteger(), nullable=False),
        sa.Column("raw_tx", sa.LargeBinary(), nullable=True),
        sa.Column("tx_hash", sa.String(length=66), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("replaced_by", sa.String(length=66), nullable=True),
        sa.ForeignKeyConstraint(
            ["intent_id"],
            ["tx_intents.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tx_hash"),
    )

    with op.batch_alter_table("tx_sends", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_tx_sends_intent_id"), ["intent_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_tx_sends_tx_hash"), ["tx_hash"], unique=True
        )

    # Create tx_receipts table
    op.create_table(
        "tx_receipts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tx_hash", sa.String(length=66), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("block_number", sa.Integer(), nullable=False),
        sa.Column("gas_used", sa.BigInteger(), nullable=False),
        sa.Column("effective_gas_price", sa.BigInteger(), nullable=False),
        sa.Column(
            "mined_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tx_hash"),
    )

    with op.batch_alter_table("tx_receipts", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_tx_receipts_tx_hash"), ["tx_hash"], unique=True
        )


def downgrade():
    """Remove transaction pipeline tables."""
    op.drop_table("tx_receipts")
    op.drop_table("tx_sends")
    op.drop_table("tx_intents")
