VACUUM ANALYZE big_rental;

DROP INDEX IF EXISTS big_rental_page_idx;
CREATE INDEX big_rental_page_idx ON big_rental (rented_at DESC, id DESC);

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20;

SELECT rented_at AS last_rented_at, id AS last_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 99979 LIMIT 1 \gset

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

(SELECT id, rented_at, customer_id FROM big_rental
 ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20)
EXCEPT
(SELECT id, rented_at, customer_id FROM big_rental
 WHERE (rented_at, id) < (:'last_rented_at', :last_id)
 ORDER BY rented_at DESC, id DESC LIMIT 20);

(SELECT id, rented_at, customer_id FROM big_rental
 WHERE (rented_at, id) < (:'last_rented_at', :last_id)
 ORDER BY rented_at DESC, id DESC LIMIT 20)
EXCEPT
(SELECT id, rented_at, customer_id FROM big_rental
 ORDER BY rented_at DESC, id DESC OFFSET 99980 LIMIT 20);

SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

SELECT rented_at AS p2_rented_at, id AS p2_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 19 LIMIT 1 \gset
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'p2_rented_at', :p2_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

SELECT rented_at AS p50k_rented_at, id AS p50k_id
FROM big_rental ORDER BY rented_at DESC, id DESC OFFSET 999979 LIMIT 1 \gset
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'p50k_rented_at', :p50k_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
ORDER BY rented_at DESC, id DESC OFFSET 999980 LIMIT 20;

DROP INDEX big_rental_page_idx;
CREATE INDEX big_rental_page_idx ON big_rental (rented_at DESC, id DESC) INCLUDE (customer_id);
VACUUM ANALYZE big_rental;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

UPDATE big_rental SET customer_id = customer_id WHERE id % 50 = 0;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;

VACUUM big_rental;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, rented_at, customer_id FROM big_rental
WHERE (rented_at, id) < (:'last_rented_at', :last_id)
ORDER BY rented_at DESC, id DESC LIMIT 20;
