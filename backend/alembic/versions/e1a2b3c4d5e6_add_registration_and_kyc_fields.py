"""add_registration_and_kyc_fields

Revision ID: e1a2b3c4d5e6
Revises: d165c639ab42
Create Date: 2026-07-10 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5e6'
down_revision = 'd165c639ab42'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- New fields on users table ---
    op.add_column('users', sa.Column('username', sa.String(100), unique=True, nullable=True))
    op.add_column('users', sa.Column('title', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('has_accepted_terms', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('users', sa.Column('kyc_submitted_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('next_of_kin_name', sa.String(200), nullable=True))
    op.add_column('users', sa.Column('next_of_kin_address', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('next_of_kin_relationship', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('next_of_kin_age', sa.Integer(), nullable=True))

    # Create index on username for fast lookups
    op.create_index('ix_users_username', 'users', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'next_of_kin_age')
    op.drop_column('users', 'next_of_kin_relationship')
    op.drop_column('users', 'next_of_kin_address')
    op.drop_column('users', 'next_of_kin_name')
    op.drop_column('users', 'kyc_submitted_at')
    op.drop_column('users', 'has_accepted_terms')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'title')
    op.drop_column('users', 'username')
