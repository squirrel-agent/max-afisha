from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("max_user_id", sa.BigInteger(), nullable=True, unique=True),
        sa.Column("city", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("categories", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("genres", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("budget_max", sa.Integer(), nullable=True),
        sa.Column("preferred_period", sa.String(length=32), nullable=True),
        sa.Column("company", sa.String(length=32), nullable=True),
        sa.Column("novelty_preference", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("profile_text", sa.Text(), nullable=True),
        sa.Column("profile_embedding", Vector(384), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("canonical_key", sa.String(length=512), nullable=True, unique=True),
        sa.Column("city", sa.String(length=64), nullable=False, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True, index=True),
        sa.Column("genres", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("venue_name", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lon", sa.Float(), nullable=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_min", sa.Integer(), nullable=True),
        sa.Column("price_max", sa.Integer(), nullable=True),
        sa.Column("is_free", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("age_min", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("primary_source", sa.String(length=64), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("ticket_url", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true(), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "events_embedding_hnsw_idx",
        "events",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "event_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("source", sa.String(length=64), nullable=False, index=True),
        sa.Column("source_event_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "interactions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(length=32), nullable=False, index=True),
        sa.Column("feed_request_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
    )

    op.create_table(
        "saved_events",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "recommendation_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "recommendation_items",
        sa.Column("request_id", sa.Uuid(), sa.ForeignKey("recommendation_requests.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("ranker_score", sa.Float(), nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("exploration", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        "source_sync_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(length=64), nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("items_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("source_sync_logs")
    op.drop_table("recommendation_items")
    op.drop_table("recommendation_requests")
    op.drop_table("saved_events")
    op.drop_table("interactions")
    op.drop_table("event_sources")
    op.drop_index("events_embedding_hnsw_idx", table_name="events")
    op.drop_table("events")
    op.drop_table("user_preferences")
    op.drop_table("users")
