from alembic import op
import sqlalchemy as sa

revision='0003_questionnaire_rec'
down_revision='0002_event_source_unique'
branch_labels=None
depends_on=None

def upgrade()->None:
    for name, typ in [
        ('when', sa.String(32)), ('when_text', sa.Text()), ('company_size', sa.String(32)), ('company_text', sa.Text()),
        ('vibe', sa.String(32)), ('vibe_text', sa.Text()), ('duration_min', sa.Integer()), ('duration_max', sa.Integer()),
        ('duration_text', sa.Text()), ('budget_text', sa.Text()), ('questionnaire_version', sa.String(32))]:
        op.add_column('user_preferences', sa.Column(name, typ, nullable=True))
    op.create_table('recommendation_ratings',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('user_id', sa.Uuid(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('request_id', sa.Uuid(), sa.ForeignKey('recommendation_requests.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('model_version', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_recommendation_ratings_user_id','recommendation_ratings',['user_id'])

def downgrade()->None:
    op.drop_index('ix_recommendation_ratings_user_id', table_name='recommendation_ratings')
    op.drop_table('recommendation_ratings')
    for name in ['questionnaire_version','budget_text','duration_text','duration_max','duration_min','vibe_text','vibe','company_text','company_size','when_text','when']:
        op.drop_column('user_preferences', name)
