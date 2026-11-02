# Exercise 4: CRUD, upsert and bulk data

All 12 operations are in `queries.sql`, run on a fresh copy of Pagila (`ex04`).

## How to run

```bash
bash scripts/create-db.sh ex04 --pagila --reset
docker compose exec -T postgres psql -U postgres -d ex04 -v ON_ERROR_STOP=1 < exercises/04-crud-bulk-data/exercise/queries.sql
```

## Results

### 1. PG-13 films longer than 120 minutes
118 rows. First: `APOLLO TEEN` (153 min). Last: `WRONG BEHAVIOR` (178 min).

### 2. Actors whose last name contains "son"
9 rows. First: `BETTE NICHOLSON`. Last: `WILL WILSON`.

### 3. Rentals not returned yet
241 rows. First: rental_id 11496. Last: rental_id 87534.

### 4. Distinct rental durations
5 rows: 3, 4, 5, 6, 7.

### 5. Third page of films (10 per page)
10 rows. First: `AMERICAN CIRCUS`. Last: `ANYTHING SAVANNAH`.

### 6. Rentals in January 2026
- With `BETWEEN '2026-01-01' AND '2026-01-31'`: **746**
- With `>= '2026-01-01' AND < '2026-02-01'`: **781**

They differ because `'2026-01-31'` means 31 January at 00:00:00, and `BETWEEN` includes both ends. Every rental made on 31 January after midnight is left out. The second version is correct, because it covers the whole month whatever the time of day.

### 7. Insert ADA LOVELACE
1 row: `actor_id` 201.

### 8. Raise rental_rate for NC-17 films shorter than 60 minutes
`SELECT count(*)` returned 21. `UPDATE ... RETURNING` returned 21 rows (`UPDATE 21`), then `COMMIT`.

### 9. Upsert of awards for actor 1 (run twice)
First run: `actor_id 1, awards 1`. Second run: `actor_id 1, awards 2`.

### 10. Insert actor 2 with `ON CONFLICT DO NOTHING` (run twice)
First run: `INSERT 0 1`. Second run: `INSERT 0 0`.

### 11. Insert 3 test payments
3 rows returned: payment_id 102095, 102096, 102097.

### 12. Delete the 3 test payments
`SELECT count(*)` returned 3. `DELETE ... RETURNING` returned 3 rows (102095, 102096, 102097), then `COMMIT`.

## Full output

The complete output of the run is in `output.txt`.