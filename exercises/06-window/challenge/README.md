# Challenge 06: gaps and islands

`islands.sql` has the query. Window functions and set operations only: no procedural code and no recursive CTE.

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ch06 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ch06 -v ON_ERROR_STOP=1 < exercises/06-window/challenge/islands.sql
```

## Result: the 10 customers with the longest islands

```
 customer_id | first_month | last_month | months 
-------------+-------------+------------+--------
          70 | 2023-06     | 2024-12    |     19
         547 | 2022-05     | 2023-10    |     18
         567 | 2022-06     | 2023-11    |     18
          33 | 2023-07     | 2024-11    |     17
         158 | 2022-11     | 2024-03    |     17
         299 | 2022-05     | 2023-09    |     17
         443 | 2023-07     | 2024-11    |     17
         533 | 2023-04     | 2024-08    |     17
         740 | 2024-07     | 2025-11    |     17
         556 | 2023-09     | 2024-12    |     16
(10 rows)

```

The first row is customer 70 with 19 months, from 2023-06 to 2024-12, and the tenth is customer 556 with 16 months, as expected. Customer 70 also rented in 2023-04, but not in 2023-05, so that gap ends the earlier island. 2025-01 has no rentals for this customer, so the island ends at 2024-12.

## How the query works

1. **`months`**: one row per customer and calendar month with at least one rental (`DISTINCT` on `date_trunc('month', rental_date)`).
2. **`numbered`**: two numbers for every row.
   - `month_no = year * 12 + month`: the month as a plain counter, so two consecutive calendar months always differ by exactly 1 (December 2023 = 24,288 and January 2024 = 24,289, so the change of year needs no special case).
   - `rn = row_number() OVER (PARTITION BY customer_id ORDER BY month)`: the position of the month in the customer's own list of months.
3. **`islands`**: `GROUP BY customer_id, month_no - rn`. This is the grouping trick (see below). Each group is one island, with `min(month)`, `max(month)` and `count(*)` months.
4. **`longest`**: `row_number() OVER (PARTITION BY customer_id ORDER BY months DESC, first_month)` numbers each customer's islands from longest to shortest, earliest first on a tie. `pick = 1` is the customer's longest island (task 1: without the final `LIMIT 10`, it returns one row per customer with rentals: 997 customers, because 647 and 978 never rented).
5. **Top 10** (task 2): `ORDER BY months DESC, customer_id LIMIT 10`.

## The technique: how `month_no - rn` groups consecutive months

Within one customer, `rn` always goes up by 1 from one row to the next. `month_no` also goes up by 1 **only if the next month is the following calendar month**. So:
- inside a run of consecutive months, both go up by 1 together, and **`month_no - rn` stays the same**;
- after a gap of k missing months, `month_no` jumps by k + 1 while `rn` still goes up by 1, so **`month_no - rn` increases by k** and a new group starts.

The difference is the same for every month of an island and different between islands, so it works as an island ID. Example with a customer who rented in January, February, March, May and June 2023:

| month | month_no | rn | month_no - rn | island |
|---|---|---|---|---|
| 2023-01 | 24277 | 1 | 24276 | A |
| 2023-02 | 24278 | 2 | 24276 | A |
| 2023-03 | 24279 | 3 | 24276 | A |
| 2023-05 | 24281 | 4 | **24277** | B (April is missing) |
| 2023-06 | 24282 | 5 | 24277 | B |

Island A is 2023-01 to 2023-03 (3 months) and island B is 2023-05 to 2023-06 (2 months). Since March and April 2022 have no rentals for anyone, nobody's island can go across them.
