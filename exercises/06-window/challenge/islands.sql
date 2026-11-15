WITH months AS (
    SELECT DISTINCT customer_id,
           date_trunc('month', rental_date)::date AS month
    FROM rental
),
numbered AS (
    SELECT customer_id, month,
           (extract(year FROM month) * 12 + extract(month FROM month))::int AS month_no,
           row_number() OVER (PARTITION BY customer_id ORDER BY month) AS rn
    FROM months
),
islands AS (
    SELECT customer_id,
           min(month) AS first_month,
           max(month) AS last_month,
           count(*)   AS months
    FROM numbered
    GROUP BY customer_id, month_no - rn
),
longest AS (
    SELECT *,
           row_number() OVER (PARTITION BY customer_id
                              ORDER BY months DESC, first_month) AS pick
    FROM islands
)
SELECT customer_id,
       to_char(first_month, 'YYYY-MM') AS first_month,
       to_char(last_month, 'YYYY-MM')  AS last_month,
       months
FROM longest
WHERE pick = 1
ORDER BY months DESC, customer_id
LIMIT 10;
