WITH RECURSIVE
edge(actor_id, other_actor_id) AS (
    SELECT fa1.actor_id, fa2.actor_id
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id <> fa1.actor_id
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING count(*) >= 3
),
walk(actor_id, distance, path) AS (
    SELECT 1, 0, ARRAY[1]
    UNION ALL
    SELECT e.other_actor_id, w.distance + 1, w.path || e.other_actor_id
    FROM walk w
    JOIN edge e ON e.actor_id = w.actor_id
    WHERE w.distance < 3
      AND e.other_actor_id <> ALL (w.path)
),
shortest AS (
    SELECT actor_id, min(distance) AS distance
    FROM walk
    WHERE actor_id <> 1
    GROUP BY actor_id
)
SELECT s.actor_id, a.first_name, a.last_name, s.distance
FROM shortest s
JOIN actor a ON a.actor_id = s.actor_id
ORDER BY s.distance, s.actor_id;

WITH RECURSIVE
edge(actor_id, other_actor_id) AS (
    SELECT fa1.actor_id, fa2.actor_id
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id <> fa1.actor_id
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING count(*) >= 3
),
walk(actor_id, distance, path) AS (
    SELECT 1, 0, ARRAY[1]
    UNION ALL
    SELECT e.other_actor_id, w.distance + 1, w.path || e.other_actor_id
    FROM walk w
    JOIN edge e ON e.actor_id = w.actor_id
    WHERE w.distance < 3
      AND e.other_actor_id <> ALL (w.path)
),
shortest AS (
    SELECT actor_id, min(distance) AS distance
    FROM walk WHERE actor_id <> 1 GROUP BY actor_id
)
SELECT distance, count(*) AS actors
FROM shortest
GROUP BY distance
ORDER BY distance;

WITH RECURSIVE
edge(actor_id, other_actor_id) AS (
    SELECT fa1.actor_id, fa2.actor_id
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id <> fa1.actor_id
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING count(*) >= 3
),
walk(actor_id, distance, path) AS (
    SELECT 1, 0, ARRAY[1]
    UNION ALL
    SELECT e.other_actor_id, w.distance + 1, w.path || e.other_actor_id
    FROM walk w
    JOIN edge e ON e.actor_id = w.actor_id
    WHERE w.distance < 5
      AND w.actor_id <> 200
      AND e.other_actor_id <> ALL (w.path)
),
best AS (
    SELECT path, distance
    FROM walk
    WHERE actor_id = 200
    ORDER BY distance, path
    LIMIT 1
)
SELECT b.distance,
       string_agg(a.first_name || ' ' || a.last_name, ' -> ' ORDER BY p.pos) AS path
FROM best b
CROSS JOIN LATERAL unnest(b.path) WITH ORDINALITY AS p(actor_id, pos)
JOIN actor a ON a.actor_id = p.actor_id
GROUP BY b.distance, b.path;
