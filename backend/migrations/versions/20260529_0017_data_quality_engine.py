"""
Add Data Quality Engine tables

Revision ID: 20260529_0017
Revises: 
Create Date: 2026-05-29
"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

revision = '20260529_0017'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'data_quality_runs',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('workspace_id', sa.String, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metrics', pg.JSONB, nullable=True),
    )
    op.create_table(
        'data_quality_findings',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('run_id', sa.Integer, sa.ForeignKey('data_quality_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workspace_id', sa.String, nullable=False),
        sa.Column('finding_type', sa.Enum(
            'DUPLICATE_DOCUMENT', 'DUPLICATE_CONTENT', 'EMPTY_DOCUMENT', 'EMPTY_CHUNK', 'ORPHAN_CHUNK',
            'ORPHAN_VERSION', 'MISSING_METADATA', 'INVALID_SOURCE_STATUS', 'INVALID_LIFECYCLE', 'RETRIEVAL_RISK',
            name='dataqualityfindingtype'), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('document_id', sa.String, nullable=True),
        sa.Column('version_id', sa.String, nullable=True),
        sa.Column('chunk_id', sa.String, nullable=True),
        sa.Column('source_status', sa.String, nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('remediation', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'data_quality_metrics',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('run_id', sa.Integer, sa.ForeignKey('data_quality_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('value', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        'data_quality_snapshots',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('workspace_id', sa.String, nullable=False),
        sa.Column('taken_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metrics', pg.JSONB, nullable=True),
        sa.Column('findings', pg.JSONB, nullable=True),
    )

def downgrade():
    op.drop_table('data_quality_snapshots')
    op.drop_table('data_quality_metrics')
    op.drop_table('data_quality_findings')
    op.drop_table('data_quality_runs')
    op.execute("DROP TYPE IF EXISTS dataqualityfindingtype")
