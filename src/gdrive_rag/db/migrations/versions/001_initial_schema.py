"""initial schema

Revision ID: 001
Revises: 
Create Date: 2024-12-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    op.create_table('sources',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=False),
    sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('last_indexed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('documents',
    sa.Column('file_id', sa.String(length=255), nullable=False),
    sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('file_name', sa.String(length=1024), nullable=False),
    sa.Column('mime_type', sa.String(length=128), nullable=False),
    sa.Column('web_view_link', sa.Text(), nullable=False),
    sa.Column('modified_time', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('owners', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('parents', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('indexed_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('file_id')
    )
    
    op.create_table('index_jobs',
    sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('job_id')
    )
    op.create_index('ix_index_jobs_source_id', 'index_jobs', ['source_id'], unique=False)
    op.create_index('ix_index_jobs_status', 'index_jobs', ['status'], unique=False)
    
    op.create_table('chunks',
    sa.Column('chunk_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('file_id', sa.String(length=255), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('chunk_text', sa.Text(), nullable=False),
    sa.Column('embedding', Vector(dim=1536), nullable=False),
    sa.Column('parent_heading', sa.String(length=512), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['documents.file_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('chunk_id')
    )
    op.create_index('ix_chunks_embedding_hnsw', 'chunks', ['embedding'], 
                    unique=False, postgresql_using='hnsw',
                    postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.create_index('ix_chunks_file_id', 'chunks', ['file_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_chunks_file_id', table_name='chunks')
    op.drop_index('ix_chunks_embedding_hnsw', table_name='chunks')
    op.drop_table('chunks')
    op.drop_index('ix_index_jobs_status', table_name='index_jobs')
    op.drop_index('ix_index_jobs_source_id', table_name='index_jobs')
    op.drop_table('index_jobs')
    op.drop_table('documents')
    op.drop_table('sources')
    op.execute('DROP EXTENSION IF EXISTS vector')
