# Challenge 05: degrees of separation with a recursive CTE

`degrees.sql` has three queries: task 2 (every actor within 3 degrees of actor 1), a summary of task 2 (actors per distance) and task 3 (shortest path from actor 1 to actor 200). Each one starts with the CTE `edge` of task 1.

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ch05 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ch05 -v ON_ERROR_STOP=1 < exercises/05-queries/challenge/degrees.sql
```

The whole file runs in about 0.15 s.

## Task 1: `edge`

```sql
edge(actor_id, other_actor_id) AS (
    SELECT fa1.actor_id, fa2.actor_id
    FROM film_actor fa1
    JOIN film_actor fa2 ON fa2.film_id = fa1.film_id AND fa2.actor_id <> fa1.actor_id
    GROUP BY fa1.actor_id, fa2.actor_id
    HAVING count(*) >= 3
)
```

The self-join on `film_id` gives every pair of actors in the same film, once per shared film. `GROUP BY` + `HAVING count(*) >= 3` keeps the pairs with at least 3 films together. Because the join produces both `(a, b)` and `(b, a)`, every connection is there in both directions. That's 1,650 directed edges (825 connections) between 199 actors. Actor 1 has 3 connections and actor 200 has 4.

## Task 2: actors within 3 degrees of actor 1

`walk` starts at actor 1 (distance 0, path `[1]`) and adds one edge per step. The result keeps the **minimum** distance of each actor (`min(distance) ... GROUP BY actor_id`), so an actor reachable by several paths appears once, with the shortest one. Actor 1 is excluded.

**141 actors.** Number of actors at each distance:

```
 distance | actors
----------+--------
        1 |      3
        2 |     23
        3 |    115
```

First rows:

```
 actor_id | first_name  |  last_name   | distance 
----------+-------------+--------------+----------
        4 | JENNIFER    | DAVIS        |        1
       20 | LUCILLE     | TRACY        |        1
       64 | RAY         | JOHANSSON    |        1
        7 | GRACE       | MOSTEL       |        2
       13 | UMA         | WOOD         |        2
       16 | FRED        | COSTNER      |        2
       17 | HELEN       | VOIGHT       |        2
       21 | KIRSTEN     | PALTROW      |        2
       24 | CAMERON     | STREEP       |        2
       29 | ALEC        | WAYNE        |        2
...
(141 rows)
```

### How I checked there are no issues

- **Distance 1 is correct:** actor 1's edges are exactly actors 4 (4 films together), 20 (3 films) and 64 (3 films), which are the 3 actors at distance 1.
- **The counts are correct:** I computed the distances again with a plain breadth-first search with no recursion and no paths (insert the neighbours of distance 0, then of distance 1, then of distance 2, skipping actors already found). It gave the same **3 / 23 / 115**.
- **No duplicates:** each `actor_id` appears once (141 rows, 141 different actors), and actor 1 isn't in the result.

## Task 3: shortest path from actor 1 to actor 200

The same walk, up to 5 steps. A path that reaches actor 200 isn't extended further. Of the paths that end at 200, the shortest is kept (`ORDER BY distance, path LIMIT 1`, where `path` breaks ties between paths of the same length so the result is always the same). Its IDs are turned into names in order with `unnest(path) WITH ORDINALITY`. If no path reaches 200 within 5 steps, `best` is empty and so is the result.

```
 distance |                                          path
----------+-----------------------------------------------------------------------------------------
        4 | PENELOPE GUINESS -> LUCILLE TRACY -> GINA DEGENERES -> ANGELINA ASTAIRE -> THORA TEMPLE
(1 row)
```

Every step is a real connection:

| From | To | Films together |
|---|---|---|
| PENELOPE GUINESS (1) | LUCILLE TRACY (20) | 3 |
| LUCILLE TRACY (20) | GINA DEGENERES (107) | 4 |
| GINA DEGENERES (107) | ANGELINA ASTAIRE (76) | 3 |
| ANGELINA ASTAIRE (76) | THORA TEMPLE (200) | 3 |

4 is the shortest distance: actor 200 isn't among the 141 actors within 3 degrees of task 2.

## How the query avoids running forever

The graph has cycles (if A is connected to B, B is connected to A), so a naive recursive walk would go A → B → A → B ... forever. Two conditions in the recursive step prevent it:

1. **The path array:** each row carries `path`, the list of actors visited so far on that path, and a step is only allowed if `e.other_actor_id <> ALL (w.path)`. A path can never visit the same actor twice, so it can never go round a cycle. And since there are only 200 actors, no path can be longer than 200 anyway.
2. **The depth limit:** `w.distance < 3` (task 2) and `w.distance < 5` (task 3) stop extending a path after 3 or 5 steps. When no row of the last step produces a new row, the recursive part returns nothing and PostgreSQL stops.

The path array alone would already make the query finish, but without the depth limit the number of paths without repeats grows very fast. The limit keeps the work small: the whole file runs in 0.15 s. In task 3, `w.actor_id <> 200` also stops a path as soon as it reaches the target, because no path that continues after 200 can be the shortest path *to* 200.
