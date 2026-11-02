-- 1. Number of films per category, including categories with no films, most films first, then by name (expected: 16 rows; Drama and Music with 152)
SELECT c.category_id, c.name, count(fc.film_id) AS films
FROM category c
LEFT JOIN film_category fc ON fc.category_id = c.category_id
GROUP BY c.category_id, c.name
ORDER BY films DESC, c.name;

-- 2. Revenue per category per month in 2025, by payment_date (expected: 192 rows; Action in January 2025 = 314.94)
SELECT c.name AS category,
       date_trunc('month', p.payment_date) AS month,
       sum(p.amount) AS revenue
FROM payment p
JOIN rental r         ON r.rental_id = p.rental_id
JOIN inventory i      ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c       ON c.category_id = fc.category_id
WHERE p.payment_date >= '2025-01-01' AND p.payment_date < '2026-01-01'
GROUP BY c.name, date_trunc('month', p.payment_date)
ORDER BY c.name, month;

-- 3. Films never rented, including films with no copy in any store (expected: 42 rows)
SELECT f.film_id, f.title
FROM film f
WHERE NOT EXISTS (
    SELECT 1
    FROM inventory i
    JOIN rental r ON r.inventory_id = i.inventory_id
    WHERE i.film_id = f.film_id
)
ORDER BY f.film_id;


-- 4. Customers who have rented films of all 5 ratings (expected: 908 rows)
SELECT c.customer_id, c.first_name, c.last_name
FROM customer c
JOIN rental r    ON r.customer_id = c.customer_id
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film f      ON f.film_id = i.film_id
GROUP BY c.customer_id, c.first_name, c.last_name
HAVING count(DISTINCT f.rating) = 5
ORDER BY c.customer_id;

-- 5. Pairs of actors who appeared together in more than 3 films, each pair once (expected: 143 rows)
SELECT fa1.actor_id AS actor_id,
       fa2.actor_id AS other_actor_id,
       a1.first_name || ' ' || a1.last_name AS actor,
       a2.first_name || ' ' || a2.last_name AS other_actor,
       count(*) AS films
FROM film_actor fa1
JOIN film_actor fa2 ON fa2.film_id = fa1.film_id
                   AND fa2.actor_id > fa1.actor_id
JOIN actor a1 ON a1.actor_id = fa1.actor_id
JOIN actor a2 ON a2.actor_id = fa2.actor_id
GROUP BY fa1.actor_id, fa2.actor_id, a1.first_name, a1.last_name, a2.first_name, a2.last_name
HAVING count(*) > 3
ORDER BY films DESC, fa1.actor_id, fa2.actor_id;

-- 6. Countries with more than 20 customers, with number of customers and total paid, most customers first (expected: 7 rows; Mexico first with 430)
SELECT co.country,
       count(*) AS customers,
       coalesce(sum(p.paid), 0) AS total_paid
FROM customer c
JOIN address a ON a.address_id = c.address_id
JOIN city ci   ON ci.city_id = a.city_id
JOIN country co ON co.country_id = ci.country_id
LEFT JOIN (
    SELECT customer_id, sum(amount) AS paid
    FROM payment
    GROUP BY customer_id
) p ON p.customer_id = c.customer_id
GROUP BY co.country_id, co.country
HAVING count(*) > 20
ORDER BY customers DESC, co.country;


-- 7. Customers who paid more in total than the average customer of their own country; no payments counts as 0 (expected: 449 rows)
WITH customer_total AS (
    SELECT c.customer_id,
           c.first_name,
           c.last_name,
           co.country_id,
           co.country,
           coalesce(p.paid, 0) AS total
    FROM customer c
    JOIN address a  ON a.address_id = c.address_id
    JOIN city ci    ON ci.city_id = a.city_id
    JOIN country co ON co.country_id = ci.country_id
    LEFT JOIN (
        SELECT customer_id, sum(amount) AS paid
        FROM payment
        GROUP BY customer_id
    ) p ON p.customer_id = c.customer_id
),
country_avg AS (
    SELECT country_id, avg(total) AS avg_total
    FROM customer_total
    GROUP BY country_id
)
SELECT ct.customer_id, ct.first_name, ct.last_name, ct.country, ct.total
FROM customer_total ct
JOIN country_avg ca ON ca.country_id = ct.country_id
WHERE ct.total > ca.avg_total
ORDER BY ct.country, ct.total DESC, ct.customer_id;

-- 8. The longest films of each rating, including ties, using a subquery (expected: 14 rows)
SELECT f.film_id, f.title, f.rating, f.length
FROM film f
WHERE f.length = (
    SELECT max(f2.length) FROM film f2 WHERE f2.rating = f.rating
)
ORDER BY f.rating, f.film_id;

-- 9. Customers with no rental on or after 2026-04-01 (expected: 49 rows)
SELECT c.customer_id, c.first_name, c.last_name
FROM customer c
WHERE NOT EXISTS (
    SELECT 1
    FROM rental r
    WHERE r.customer_id = c.customer_id
      AND r.rental_date >= '2026-04-01'
)
ORDER BY c.customer_id;

-- 10. Average days a film stays out per category, returned rentals only, rounded to 2 decimals, highest first (expected: 16 rows; Sci-Fi first with 5.30)
SELECT c.name AS category,
       round(avg(extract(epoch FROM (r.return_date - r.rental_date)) / 86400)::numeric, 2) AS avg_days
FROM rental r
JOIN inventory i      ON i.inventory_id = r.inventory_id
JOIN film_category fc ON fc.film_id = i.film_id
JOIN category c       ON c.category_id = fc.category_id
WHERE r.return_date IS NOT NULL
GROUP BY c.category_id, c.name
ORDER BY avg_days DESC, c.name;