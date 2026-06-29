"""Initial migration

Revision ID: 813d22806760
Revises: 
Create Date: 2026-01-03 20:40:04.975135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '813d22806760'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('date_of_birth', sa.DateTime(), nullable=True),
        sa.Column('registration_date', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('account_status', sa.String(length=20), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_index(op.f('ix_users_user_id'), 'users', ['user_id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)

    op.create_table(
        'images',
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('upload_timestamp', sa.DateTime(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(length=10), nullable=False),
        sa.Column('resolution', sa.String(length=20), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('storage_bucket', sa.String(length=100), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('image_id'),
    )
    op.create_index(op.f('ix_images_image_id'), 'images', ['image_id'], unique=False)

    op.create_table(
        'predictions',
        sa.Column('prediction_id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('module_a_result', sa.String(length=50), nullable=False),
        sa.Column('module_a_confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('module_b_result', sa.String(length=50), nullable=True),
        sa.Column('module_b_confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('gradcam_path', sa.String(length=500), nullable=True),
        sa.Column('prediction_timestamp', sa.DateTime(), nullable=False),
        sa.Column('processing_time', sa.Integer(), nullable=True),
        sa.Column('ml_context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.Column('is_flagged', sa.Boolean(), nullable=False),
        sa.Column('flag_reason', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['image_id'], ['images.image_id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('prediction_id'),
        sa.UniqueConstraint('image_id'),
    )
    op.create_index(op.f('ix_predictions_prediction_id'), 'predictions', ['prediction_id'], unique=False)

    op.create_table(
        'conversations',
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('prediction_id', sa.Integer(), nullable=True),
        sa.Column('message_timestamp', sa.DateTime(), nullable=False),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('intent_classified', sa.String(length=50), nullable=False),
        sa.Column('intent_confidence', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('system_response', sa.Text(), nullable=False),
        sa.Column('safety_flag', sa.Boolean(), nullable=False),
        sa.Column('llm_tokens_used', sa.Integer(), nullable=True),
        sa.Column('context_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('conversation_session', sa.UUID(), nullable=True),
        sa.Column('llm_model_used', sa.String(length=50), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['prediction_id'], ['predictions.prediction_id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('conversation_id'),
    )
    op.create_index(op.f('ix_conversations_conversation_id'), 'conversations', ['conversation_id'], unique=False)

    op.create_table(
        'system_logs',
        sa.Column('log_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('log_type', sa.String(length=50), nullable=False),
        sa.Column('log_message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('http_method', sa.String(length=10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id']),
        sa.PrimaryKeyConstraint('log_id'),
    )
    op.create_index(op.f('ix_system_logs_log_id'), 'system_logs', ['log_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_system_logs_log_id'), table_name='system_logs')
    op.drop_table('system_logs')
    op.drop_index(op.f('ix_conversations_conversation_id'), table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_predictions_prediction_id'), table_name='predictions')
    op.drop_table('predictions')
    op.drop_index(op.f('ix_images_image_id'), table_name='images')
    op.drop_table('images')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_user_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
