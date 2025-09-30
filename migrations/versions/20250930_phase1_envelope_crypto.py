"""Phase 1: Envelope encryption for API credentials and wallet keys.

Revision ID: 20250930_phase1_envelope_crypto
Revises: xxxx_envelope_encryption
Create Date: 2025-09-30 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20250930_phase1_envelope_crypto"
down_revision = "xxxx_envelope_encryption"
branch_labels = None
depends_on = None


def upgrade():
    """Add envelope-encrypted columns and api_credentials table."""
    # Add new envelope-encrypted column to wallets
    with op.batch_alter_table("wallets", schema=None) as batch_op:
        batch_op.add_column(sa.Column("privkey_enc", sa.LargeBinary(), nullable=True))

    # Create api_credentials table for encrypted API secrets
    op.create_table(
        "api_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("secret_enc", sa.LargeBinary(), nullable=True),
        sa.Column("meta_enc", sa.LargeBinary(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes
    with op.batch_alter_table("api_credentials", schema=None) as batch_op:
        batch_op.create_index("idx_api_creds_user_provider", ["user_id", "provider"])
        batch_op.create_index(
            batch_op.f("ix_api_credentials_user_id"), ["user_id"], unique=False
        )


def downgrade():
    """Remove envelope-encrypted columns and api_credentials table."""
    # Drop api_credentials table
    op.drop_table("api_credentials")

    # Remove envelope-encrypted column from wallets
    with op.batch_alter_table("wallets", schema=None) as batch_op:
        batch_op.drop_column("privkey_enc")
