# Exercise 5: Joins, aggregation, subqueries and CTEs

The 10 queries are in `queries.sql`, run on a fresh copy of Pagila (`ex05`). No window functions are used.

## How to run

```bash
bash scripts/create-db.sh ex05 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex05 -v ON_ERROR_STOP=1 < exercises/05-joins-aggregation-ctes/exercise/queries.sql
```

## Results

Each result shows the row count and the first 5 rows.

### 1. Number of films per category (16 rows)

```
 category_id |    name     | films 
-------------+-------------+-------
           7 | Drama       |   152
          12 | Music       |   152
          16 | Travel      |   151
           3 | Children    |   150
           9 | Foreign     |   150
(16 rows)
```

### 2. Revenue per category per month in 2025 (192 rows)

```
  category   |         month          | revenue 
-------------+------------------------+---------
 Action      | 2025-01-01 00:00:00+00 |  314.94
 Action      | 2025-02-01 00:00:00+00 |  317.99
 Action      | 2025-03-01 00:00:00+00 |  370.90
 Action      | 2025-04-01 00:00:00+00 |  379.83
 Action      | 2025-05-01 00:00:00+00 |  384.76
(192 rows)
```

### 3. Films never rented (42 rows)

```
 film_id |         title          
---------+------------------------
      14 | ALICE FANTASIA
      33 | APOLLO TEEN
      36 | ARGONAUTS TOWN
      38 | ARK RIDGEMONT
      41 | ARSENIC INDEPENDENCE
(42 rows)
```

### 4. Customers who rented films of all 5 ratings (908 rows)

```
 customer_id | first_name  |  last_name   
-------------+-------------+--------------
           1 | MARY        | SMITH
           2 | PATRICIA    | JOHNSON
           3 | LINDA       | WILLIAMS
           4 | BARBARA     | JONES
           5 | ELIZABETH   | BROWN
(908 rows)
```

### 5. Pairs of actors in more than 3 films together (143 rows)

```
 actor_id | other_actor_id |        actor        |    other_actor     | films 
----------+----------------+---------------------+--------------------+-------
       27 |             60 | JULIA MCQUEEN       | HENRY BERRY        |     7
       15 |            198 | CUBA OLIVIER        | MARY KEITEL        |     6
       21 |            108 | KIRSTEN PALTROW     | WARREN NOLTE       |     6
       37 |            188 | VAL BOLGER          | ROCK DUKAKIS       |     6
       83 |            161 | BEN WILLIS          | HARVEY HOPE        |     6
(143 rows)
```

`fa2.actor_id > fa1.actor_id` lists each pair once and excludes an actor paired with themselves.

### 6. Countries with more than 20 customers (7 rows)

```
      country       | customers | total_paid 
--------------------+-----------+------------
 Mexico             |       430 |   35650.03
 India              |        60 |   14182.51
 China              |        53 |   12389.30
 United States      |        36 |    8618.76
 Japan              |        31 |    7287.91
(7 rows)
```

Payments are summed per customer in a subquery before joining, so each payment is counted once.

### 7. Customers who paid more than the average customer of their country (449 rows)

```
 customer_id | first_name  |  last_name   |                country                | total  
-------------+-------------+--------------+---------------------------------------+--------
         176 | JUNE        | CARROLL      | Algeria                               | 280.26
         528 | CLAUDE      | HERZOG       | Angola                                | 256.30
         359 | WILLIE      | MARKHAM      | Argentina                             | 293.17
          89 | JULIA       | FLORES       | Argentina                             | 284.22
         560 | JORDAN      | ARCHULETA    | Argentina                             | 273.27
(449 rows)
```

Customers with no payments count as 0 (`coalesce`) in the country average.

### 8. Longest films of each rating, including ties (14 rows)

```
 film_id |       title        | rating | length 
---------+--------------------+--------+--------
     182 | CONTROL ANTHEM     | G      |    185
     212 | DARN FORRESTER     | G      |    185
     609 | MUSCLE BRIGHT      | G      |    185
     991 | WORST BANGER       | PG     |    185
     141 | CHICAGO NORTH      | PG-13  |    185
(14 rows)
```

### 9. Customers with no rental on or after 2026-04-01 (49 rows)

```
 customer_id | first_name |  last_name  
-------------+------------+-------------
           9 | MARGARET   | MOORE
          13 | KAREN      | JACKSON
          21 | MICHELLE   | CLARK
          46 | CATHERINE  | CAMPBELL
          52 | JULIE      | SANCHEZ
(49 rows)
```

### 10. Average days a film stays out per category (16 rows)

```
  category   | avg_days 
-------------+----------
 Sci-Fi      |     5.30
 Music       |     5.27
 Sports      |     5.26
 Drama       |     5.18
 Children    |     5.17
(16 rows)
```

Returned rentals only (`return_date IS NOT NULL`).