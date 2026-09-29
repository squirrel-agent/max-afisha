from alembic import op

revision = "0002_event_source_unique"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_event_source_external",
        "event_sources",
        ["source", "source_event_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_event_source_external",
        "event_sources",
        type_="unique",
    )
