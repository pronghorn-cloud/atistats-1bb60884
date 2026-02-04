"""Initial schema - Public Bodies and ATI Requests

Revision ID: 001_initial
Revises: None
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""
    
    # Create enum types
    request_type_enum = postgresql.ENUM(
        'personal', 'non_personal', 'mixed', 'correction',
        name='request_type',
        create_type=True
    )
    request_status_enum = postgresql.ENUM(
        'received', 'in_progress', 'pending_clarification', 'extended',
        'completed', 'abandoned', 'transferred',
        name='request_status',
        create_type=True
    )
    request_outcome_enum = postgresql.ENUM(
        'full_disclosure', 'partial_disclosure', 'no_disclosure',
        'no_records_exist', 'transferred', 'abandoned', 'withdrawn', 'pending',
        name='request_outcome',
        create_type=True
    )
    
    # Create public_bodies table
    op.create_table(
        'public_bodies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('abbreviation', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('website_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    
    # Create ati_requests table
    op.create_table(
        'ati_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('request_number', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('public_body_id', postgresql.UUID(as_uuid=True), 
                  sa.ForeignKey('public_bodies.id', ondelete='RESTRICT'), 
                  nullable=False, index=True),
        sa.Column('submission_date', sa.Date(), nullable=False, index=True),
        sa.Column('request_type', request_type_enum, nullable=False),
        sa.Column('status', request_status_enum, nullable=False, index=True),
        sa.Column('outcome', request_outcome_enum, nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('extension_days', sa.Integer(), nullable=False, default=0),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('pages_processed', sa.Integer(), nullable=True),
        sa.Column('pages_disclosed', sa.Integer(), nullable=True),
        sa.Column('fees_charged', sa.Float(), nullable=True),
        sa.Column('is_deemed_refusal', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop all tables and enum types."""
    op.drop_table('ati_requests')
    op.drop_table('public_bodies')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS request_outcome')
    op.execute('DROP TYPE IF EXISTS request_status')
    op.execute('DROP TYPE IF EXISTS request_type')
