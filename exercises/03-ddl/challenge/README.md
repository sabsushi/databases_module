# Challenge 03: a domain that rejects invalid ISBN-13 values

`isbn.sql` has the function `is_valid_isbn13`, the domain `isbn13`, the `book` table and the 7 test inserts.

## How to run

From the repository root (no `ON_ERROR_STOP`, because 4 inserts are expected to fail):

```bash
bash scripts/create-db.sh ch03 --reset
docker compose exec -T postgres psql -U postgres -d ch03 < exercises/03-ddl/challenge/isbn.sql
```

(PowerShell: `Get-Content exercises/03-ddl/challenge/isbn.sql | docker compose exec -T postgres psql -U postgres -d ch03`.)

## How the function works

```sql
CREATE FUNCTION is_valid_isbn13(value text) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
RETURN
    value ~ '^[0-9](-?[0-9])*$'
    AND length(replace(value, '-', '')) = 13
    AND (check digit computed from the first 12 digits) = 13th digit;
```

1. **Format:** `^[0-9](-?[0-9])*$` means "a digit, then any number of (an optional single hyphen followed by a digit)". So the value starts and ends with a digit, a hyphen is always between two digits, and two hyphens can never be next to each other. Anything that isn't a digit or a hyphen is rejected.
2. **Length:** with the hyphens removed, exactly 13 digits.
3. **Check digit:** `generate_series(1, 12)` walks the first 12 digits. Odd positions are multiplied by 1 and even positions by 3, then the products are added up. The result must be `(10 - sum % 10) % 10`, compared with the 13th digit. The outer `% 10` turns a 10 into 0 (as with `978-3-16-148410-0`).

`AND` stops at the first false condition, so the check digit is only computed for values that already have the right format.

## Output of `isbn.sql`

```
DROP TABLE
DROP DOMAIN
DROP FUNCTION
CREATE FUNCTION
CREATE DOMAIN
CREATE TABLE
INSERT 0 1
INSERT 0 1
INSERT 0 1
isbn.sql:46: ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
isbn.sql:48: ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
isbn.sql:50: ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
isbn.sql:52: ERROR:  value for domain isbn13 violates check constraint "isbn13_check"
 book_id |       isbn        |         title         
---------+-------------------+-----------------------
       1 | 978-0-306-40615-7 | Valid with hyphens
       2 | 9781402894626     | Valid without hyphens
       3 | 978-3-16-148410-0 | Valid, check digit 0
(3 rows)

```

| Value | Expected | Result |
|---|---|---|
| `978-0-306-40615-7` | accepted | `INSERT 0 1` |
| `9781402894626` | accepted | `INSERT 0 1` |
| `978-3-16-148410-0` | accepted | `INSERT 0 1` |
| `978-0-306-40615-8` (wrong check digit) | rejected | `ERROR: value for domain isbn13 violates check constraint "isbn13_check"` |
| `978-0-306-4061` (too short) | rejected | same error |
| `-9780306406157` (leading hyphen) | rejected | same error |
| `978--0306406157` (two hyphens in a row) | rejected | same error |

I also tested a trailing hyphen (`978-0-306-40615-7-`), 14 digits and a letter, and the function returned `false` for all three.

## Why the function must be `IMMUTABLE`

`IMMUTABLE` promises PostgreSQL that the function **always returns the same result for the same input**, and that it doesn't read the database or depend on anything else (time, settings, other tables). That's true here: the result depends only on the text of the ISBN.

It matters because of how constraints work. PostgreSQL checks a `CHECK` constraint (here, the domain's) **only when a value is written**, and never again. A row that was valid when inserted is assumed to stay valid forever. That assumption is only correct if the function always gives the same answer. If it could change its mind (for example, if it read a table of "allowed prefixes", or depended on the time or a session setting), rows already stored could become invalid without anyone noticing, and a dump could fail to restore, because the restore checks every row again with the function as it is then.

Marking it `IMMUTABLE` also lets PostgreSQL use it wherever it requires that guarantee, for example in an **expression index** (`CREATE INDEX ON book (is_valid_isbn13(isbn))` only works with an `IMMUTABLE` function, as exercise 07 showed with `rented_at::date`), and evaluate it once for a constant at planning time. Writing `IMMUTABLE` on a function that isn't really immutable would be lying to the planner, and leads to the wrong results described above.

(`STRICT` makes the function return NULL for a NULL input without running it. A NULL passes a `CHECK`, but the `isbn` column is `NOT NULL`, so NULLs are rejected anyway.)
