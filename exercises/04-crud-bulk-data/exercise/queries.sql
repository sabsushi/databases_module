-- 1. PG-13 films longer than 120 minutes, sorted by title (expected: 118 rows)
SELECT film_id, title, length, rating
FROM film
WHERE rating = 'PG-13' AND length > 120
ORDER BY title;

-- 2. Actors whose last name contains "son", any case (expected: 9 rows)
SELECT actor_id, first_name, last_name
FROM actor
WHERE last_name ILIKE '%son%';

-- 3. Rentals not returned yet (expected: 241 rows)
SELECT rental_id, rental_date, inventory_id, customer_id
FROM rental
WHERE return_date IS NULL;

-- 4. Distinct rental durations, ascending (expected: 5 rows, 3 to 7)
SELECT DISTINCT rental_duration
FROM film
ORDER BY rental_duration;

-- 5. Third page of films, 10 per page (expected: 10 rows, AMERICAN CIRCUS to ANYTHING SAVANNAH)
SELECT film_id, title
FROM film
ORDER BY title
LIMIT 10 OFFSET 20;

-- 6. Rentals in January 2026, written twice (expected: 746 and 781)
SELECT count(*) AS with_between
FROM rental
WHERE rental_date BETWEEN '2026-01-01' AND '2026-01-31';

SELECT count(*) AS with_half_open_range
FROM rental
WHERE rental_date >= '2026-01-01' AND rental_date < '2026-02-01';
-- Why they differ: '2026-01-31' means 2026-01-31 00:00:00, and BETWEEN includes
-- both ends. So every rental made during 31 January after midnight is left out.
-- The second version (>= start, < start of next month) is correct, because it
-- covers the whole month whatever the time of day.

-- 7. Insert actor ADA LOVELACE and return the generated key (expected: actor_id 201)
INSERT INTO actor (first_name, last_name)
VALUES ('ADA', 'LOVELACE')
RETURNING actor_id, last_update;

-- 8. Raise rental_rate by 0.50 for NC-17 films shorter than 60 minutes (expected: 21 and 21)
BEGIN;
SELECT count(*) FROM film WHERE rating = 'NC-17' AND length < 60;
UPDATE film
SET rental_rate = rental_rate + 0.50
WHERE rating = 'NC-17' AND length < 60
RETURNING film_id, title, rental_rate;
COMMIT;

-- 9. Upsert: add one award to actor 1, run twice (expected: awards = 2)
CREATE TABLE actor_award (
    actor_id integer PRIMARY KEY REFERENCES actor,
    awards   integer NOT NULL DEFAULT 0
);

INSERT INTO actor_award (actor_id, awards) VALUES (1, 1)
ON CONFLICT (actor_id) DO UPDATE SET awards = actor_award.awards + 1
RETURNING *;

INSERT INTO actor_award (actor_id, awards) VALUES (1, 1)
ON CONFLICT (actor_id) DO UPDATE SET awards = actor_award.awards + 1
RETURNING *;

-- 10. Actor 2 with 5 awards, DO NOTHING, run twice (expected: INSERT 0 1, then INSERT 0 0)
INSERT INTO actor_award (actor_id, awards) VALUES (2, 5)
ON CONFLICT DO NOTHING;

INSERT INTO actor_award (actor_id, awards) VALUES (2, 5)
ON CONFLICT DO NOTHING;

-- 11. Insert 3 test payments in one statement (expected: 3 rows)
INSERT INTO payment (customer_id, staff_id, rental_id, amount, payment_date)
VALUES (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
       (1, 2, 76, 0.01, '2026-07-30 12:00+00'),
       (1, 2, 76, 0.01, '2026-07-30 12:00+00')
RETURNING payment_id;

-- 12. Delete the 3 test payments (expected: 3 and 3)
BEGIN;
SELECT count(*)
FROM payment
WHERE customer_id = 1 AND staff_id = 2 AND rental_id = 76
  AND amount = 0.01 AND payment_date = '2026-07-30 12:00+00';
DELETE FROM payment
WHERE customer_id = 1 AND staff_id = 2 AND rental_id = 76
  AND amount = 0.01 AND payment_date = '2026-07-30 12:00+00'
RETURNING payment_id;
COMMIT;
