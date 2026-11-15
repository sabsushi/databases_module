# Exercise 6: Window functions and views

The 6 tasks are in `queries.sql`, run on a fresh copy of Pagila (`ex06`).

## How to run

```bash
bash scripts/create-db.sh ex06 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex06 -v ON_ERROR_STOP=1 < exercises/06-window/exercise/queries.sql
```

## Results

Each result shows the row count and the first 5 rows.

### 1. The 3 most rented films of each category (56 rows)

`DENSE_RANK` is used so that tied films share a position and the next position is not skipped. That way every film in positions 1, 2 and 3 is listed (for example, Animation has two films tied in first place, and positions 2 and 3 are still shown).

```
 category  | pos | film_id |      title      | rentals
-----------+-----+---------+-----------------+---------
 Action    |   1 |     127 | CAT CONEHEADS   |     123
 Action    |   2 |     773 | SEABISCUIT PUNK |      96
 Action    |   3 |     450 | IDOLS SNATCHERS |      92
 Animation |   1 |     358 | GILMORE BOILED  |     102
 Animation |   1 |     382 | GRIT CLOCKWORK  |     102
(56 rows)
```

### 2. Revenue per day in July 2026 with running total (28 rows)

```
    day     | revenue | running_total
------------+---------+---------------
 2026-07-01 |   67.78 |         67.78
 2026-07-02 |   89.62 |        157.40
 2026-07-03 |   61.78 |        219.18
 2026-07-04 |   97.66 |        316.84
 2026-07-05 |   46.81 |        363.65
(28 rows)
```

Last row: `2026-07-28 | 426.58 | 2409.88`.

### 3. Revenue per month with change from the previous month (55 rows)

```
   month    | revenue  | previous_revenue | change  | change_pct
------------+----------+------------------+---------+------------
 2022-01-01 |  3094.78 |                  |         |
 2022-02-01 | 10164.97 |          3094.78 | 7070.19 |      228.5
 2022-03-01 | 11413.86 |         10164.97 | 1248.89 |       12.3
 2022-04-01 | 10759.52 |         11413.86 | -654.34 |       -5.7
 2022-05-01 | 11347.28 |         10759.52 |  587.76 |        5.5
(55 rows)
```

July 2026: `2026-07-01 | 2409.88 | 2105.73 | 304.15 | 14.4`. The first month has no previous month, so `LAG` returns NULL and the change is empty.

### 4. Each customer's position in their store by total paid (999 rows)

`LEFT JOIN` keeps customers with no payments and `coalesce` turns their total into 0. `RANK` makes tied customers share a position.

```
 store_id | pos | customer_id | first_name | last_name | total_paid
----------+-----+-------------+------------+-----------+------------
        1 |   1 |         468 | TIM        | CARY      |     344.06
        1 |   2 |         380 | RUSSELL    | BRINSON   |     324.04
        1 |   3 |         368 | HARRY      | ARCE      |     323.17
        1 |   4 |         295 | DAISY      | BATES     |     322.12
        1 |   5 |          22 | LAURA      | RODRIGUEZ |     320.17
(999 rows)
```

First in store 2: `2 | 1 | 526 | KARL | SEAL | 358.12`.

### 5. Top 5 customers of each store (10 rows)

```
 store_id | pos | customer_id | first_name | last_name | total_paid
----------+-----+-------------+------------+-----------+------------
        1 |   1 |         468 | TIM        | CARY      |     344.06
        1 |   2 |         380 | RUSSELL    | BRINSON   |     324.04
        1 |   3 |         368 | HARRY      | ARCE      |     323.17
        1 |   4 |         295 | DAISY      | BATES     |     322.12
        1 |   5 |          22 | LAURA      | RODRIGUEZ |     320.17
        2 |   1 |         526 | KARL       | SEAL      |     358.12
        2 |   2 |         410 | CURTIS     | IRBY      |     317.10
        2 |   3 |         120 | SYLVIA     | ORTIZ     |     315.12
        2 |   4 |         469 | WESLEY     | BULL      |     311.18
        2 |   5 |         178 | MARION     | SNYDER    |     304.17
(10 rows)
```

The window function cannot go in `WHERE`, so the ranking is done in a CTE and filtered in the outer query.

### 6. Materialised view `monthly_revenue`

The view stores revenue per month. It has a unique index on `month`, which `REFRESH MATERIALIZED VIEW CONCURRENTLY` requires.

Output of the steps:


**6a. Before**

```
   month    | revenue
------------+---------
 2026-07-01 | 2409.88
(1 row)

```

**6b. Insert a test payment of 100.00 in July 2026**

```
 payment_id | amount |      payment_date
------------+--------+------------------------
     102095 | 100.00 | 2026-07-15 12:00:00+00
(1 row)
INSERT 0 1

```

**6c. The view is stale, the table is not**

```
   month    | revenue
------------+---------
 2026-07-01 | 2409.88
(1 row)

 live_revenue
--------------
      2509.88
(1 row)

```

**6d. After REFRESH MATERIALIZED VIEW CONCURRENTLY**

```
REFRESH MATERIALIZED VIEW
   month    | revenue
------------+---------
 2026-07-01 | 2509.88
(1 row)
```

The view keeps showing 2409.88 after the insert, because it stores the result of the query and does not read `payment` again. Only after the refresh does it show 2509.88.
