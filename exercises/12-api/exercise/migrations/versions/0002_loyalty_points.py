import sqlalchemy as sa
from alembic import op

revision = "0002_loyalty_points"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "customer",
        sa.Column("loyalty_points", sa.Integer(), nullable=True, server_default=sa.text("0")),
    )
    op.execute(
        """
        UPDATE customer c
        SET loyalty_points = (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id)
        """
    )
    op.alter_column("customer", "loyalty_points", nullable=False)

def downgrade() -> None:
    op.drop_column("customer", "loyalty_points")
