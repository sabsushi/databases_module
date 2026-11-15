-- 1.
WITH film_rentals AS (
    SELECT c.name AS category, f.film_id, f.title, count(r.rental_id) AS rentals
    FROM film f
    JOIN film_category fc ON fc.film_id = f.film_id
    JOIN category c       ON c.category_id = fc.category_id
    JOIN inventory i      ON i.film_id = f.film_id
    JOIN rental r         ON r.inventory_id = i.inventory_id
    GROUP BY c.name, f.film_id, f.title
),
ranked AS (
    SELECT category, film_id, title, rentals,
           DENSE_RANK() OVER (PARTITION BY category ORDER BY rentals DESC) AS pos
    FROM film_rentals
)
SELECT category, pos, film_id, title, rentals
FROM ranked
WHERE pos <= 3
ORDER BY category, pos, title;

-- 2.
WITH daily AS (
    SELECT payment_date::date AS day, sum(amount) AS revenue
    FROM payment
    WHERE payment_date >= '2026-07-01' AND payment_date < '2026-08-01'
    GROUP BY payment_date::date
)
SELECT day, revenue,
       SUM(revenue) OVER (ORDER BY day) AS running_total
FROM daily
ORDER BY day;

-- 3.
WITH monthly AS (
    SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
    FROM payment
    GROUP BY 1
)
SELECT month, revenue,
       LAG(revenue) OVER (ORDER BY month) AS previous_revenue,
       revenue - LAG(revenue) OVER (ORDER BY month) AS change,
       round(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS change_pct
FROM monthly
ORDER BY month;

-- 4.
WITH totals AS (
    SELECT c.customer_id, c.store_id, c.first_name, c.last_name,
           coalesce(sum(p.amount), 0) AS total_paid
    FROM customer c
    LEFT JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id, c.store_id, c.first_name, c.last_name
)
SELECT store_id,
       RANK() OVER (PARTITION BY store_id ORDER BY total_paid DESC) AS pos,
       customer_id, first_name, last_name, total_paid
FROM totals
ORDER BY store_id, pos, customer_id;

-- 5.
WITH totals AS (
    SELECT c.customer_id, c.store_id, c.first_name, c.last_name,
           coalesce(sum(p.amount), 0) AS total_paid
    FROM customer c
    LEFT JOIN payment p ON p.customer_id = c.customer_id
    GROUP BY c.customer_id, c.store_id, c.first_name, c.last_name
),
ranked AS (
    SELECT *, RANK() OVER (PARTITION BY store_id ORDER BY total_paid DESC) AS pos
    FROM totals
)
SELECT store_id, pos, customer_id, first_name, last_name, total_paid
FROM ranked
WHERE pos <= 5
ORDER BY store_id, pos, customer_id;

-- 6.
DROP MATERIALIZED VIEW IF EXISTS monthly_revenue;

CREATE MATERIALIZED VIEW monthly_revenue AS
SELECT date_trunc('month', payment_date)::date AS month, sum(amount) AS revenue
FROM payment
GROUP BY 1;

CREATE UNIQUE INDEX monthly_revenue_month_idx ON monthly_revenue (month);

SELECT month, revenue FROM monthly_revenue WHERE month = '2026-07-01';

INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES (1, 1, 1, 100.00, '2026-07-15 12:00:00+00')
RETURNING payment_id, amount, payment_date;

SELECT month, revenue FROM monthly_revenue WHERE month = '2026-07-01';
SELECT sum(amount) AS live_revenue FROM payment
WHERE payment_date >= '2026-07-01' AND payment_date < '2026-08-01';

REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_revenue;
SELECT month, revenue FROM monthly_revenue WHERE month = '2026-07-01';
