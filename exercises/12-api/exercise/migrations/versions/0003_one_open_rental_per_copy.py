from alembic import op

revision = "0003_one_open_rental_per_copy"
down_revision = "0002_loyalty_points"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute(
        """
        WITH open_rentals AS (
            SELECT rental_id,
                   row_number()  OVER w AS pos,
                   first_value(rental_date) OVER w AS newest_rental_date
            FROM rental
            WHERE return_date IS NULL
            WINDOW w AS (PARTITION BY inventory_id ORDER BY rental_date DESC, rental_id DESC)
        )
        UPDATE rental r
        SET return_date = o.newest_rental_date
        FROM open_rentals o
        WHERE r.rental_id = o.rental_id
          AND o.pos > 1
        """
    )
    op.create_index(
        "rental_one_open_per_copy",
        "rental",
        ["inventory_id"],
        unique=True,
        postgresql_where="return_date IS NULL",
    )

def downgrade() -> None:
    op.drop_index("rental_one_open_per_copy", table_name="rental")
