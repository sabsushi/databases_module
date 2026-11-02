# Exercise 3: DDL and constraints

Municipal library schema in PostgreSQL (`schema.sql`) and five statements that must fail (`invalid.sql`).

## How to run

```powershell
docker compose exec -T postgres createdb -U postgres ex03
Get-Content exercises/03-ddl-constraints/schema.sql | docker compose exec -T postgres psql -U postgres -d ex03 -v ON_ERROR_STOP=1
Get-Content exercises/03-ddl-constraints/invalid.sql | docker compose exec -T postgres psql -U postgres -d ex03
```

## Output of `invalid.sql`

```
INSERT 0 1
INSERT 0 1
INSERT 0 1
INSERT 0 1
ERROR:  duplicate key value violates unique constraint "member_email_unique"
DETAIL:  Key (email)=(ana@example.com) already exists.
ERROR:  new row for relation "loan" violates check constraint "due_after_loan"
DETAIL:  Failing row contains (2, 1, 1, 2025-02-01, 2025-01-01, 0.00).
ERROR:  duplicate key value violates unique constraint "copy_book_number_unique"
DETAIL:  Key (book_id, copy_number)=(1, 1) already exists.
ERROR:  insert or update on table "loan" violates foreign key constraint "loan_member_id_fkey"
DETAIL:  Key (member_id)=(999) is not present in table "member".
ERROR:  update or delete on table "copy" violates RESTRICT setting of foreign key constraint "loan_copy_id_fkey" on table "loan"
DETAIL:  Key (copy_id)=(1) is referenced from table "loan".
```

## Constraints tested

| Statement | Constraint | Type |
|---|---|---|
| Duplicate member email | `member_email_unique` | UNIQUE |
| Due date before loan date | `due_after_loan` | CHECK |
| Same copy number for the same book | `copy_book_number_unique` | Composite UNIQUE |
| Loan for a member that doesn't exist | `loan_member_id_fkey` | FOREIGN KEY |
| Delete a copy that has a loan | `loan_copy_id_fkey` | FOREIGN KEY (RESTRICT) |