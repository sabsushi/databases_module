# Exercise 9: Security

Files:

| File | Task |
|---|---|
| `roles.sql` | 1. Login roles `ex09_migrations`, `ex09_app`, `ex09_readonly` and their privileges |
| `proofs.sql` | 2. Proofs with `SET ROLE` / `RESET ROLE` |
| `api/` | 3. FastAPI project with `POST /actors`, `POST /notes`, `POST /counters/{name}` |
| `api/.env.example` | Every variable the API and the setup scripts need |
| `api/scripts/setup_mongo.py` | Creates the MongoDB user `ex09_app` (`readWrite` on `ex09` only) |
| `api/scripts/setup_redis.py` | Creates the Redis ACL user `ex09_app` |

No password is written in the code: `roles.sql` takes them as `psql` variables, and the API and scripts read them from `.env`.

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ex09 --pagila --reset

docker compose exec -T postgres psql -U postgres -d ex09 -v ON_ERROR_STOP=1 \
  -v migrations_password=... -v app_password=... -v readonly_password=... \
  < exercises/09-security/exercise/roles.sql

docker compose exec -T postgres psql -U postgres -d ex09 < exercises/09-security/exercise/proofs.sql
```

Then, in `exercises/09-security/exercise/api/`:

```bash
cp .env.example .env
uv sync
uv run --env-file .env python -m scripts.setup_mongo
uv run --env-file .env python -m scripts.setup_redis
uv run --env-file .env uvicorn app.main:app --port 8000
```

## Task 1: roles

`roles.sql` creates the three login roles only if they don't exist yet, so it can be run again. Then it:

- makes `ex09_migrations` the owner of `ex09`, with `CREATE` on `public` (it's the only role that changes the schema);
- runs `REVOKE CREATE ON SCHEMA public FROM PUBLIC`, so no other role can create tables;
- grants `ex09_app` `SELECT, INSERT, UPDATE, DELETE` on every table and `USAGE` on every sequence (`INSERT` into `actor` needs the sequence for `actor_id`);
- grants `ex09_readonly` `SELECT` on every table;
- adds `ALTER DEFAULT PRIVILEGES FOR ROLE ex09_migrations` so that tables (and sequences) created later by `ex09_migrations` get the same grants.

## Task 2: output of `proofs.sql`

```
SET
proofs.sql:7: ERROR:  must be owner of table film
RESET
SET
INSERT 0 1
RESET
SET
 count
-------
  1000
(1 row)

RESET
SET
proofs.sql:22: ERROR:  permission denied for table actor
RESET
SET
CREATE TABLE
RESET
SET
INSERT 0 1
RESET
SET
DROP TABLE
RESET
DELETE 1
```

| Statement | Expected | Result |
|---|---|---|
| `ex09_app`: `DROP TABLE film` | fails | `ERROR: must be owner of table film` ✓ |
| `ex09_app`: `INSERT INTO actor ...` | works | `INSERT 0 1` ✓ |
| `ex09_readonly`: `SELECT count(*) FROM film` | works | `1000` ✓ |
| `ex09_readonly`: `INSERT INTO actor ...` | fails | `ERROR: permission denied for table actor` ✓ |
| extra: table created by `ex09_migrations`, then `INSERT` as `ex09_app` | works | `INSERT 0 1` ✓ (default privileges) |

## Task 3: users in MongoDB and Redis, and the API

### MongoDB user (`scripts/setup_mongo.py`)

```
Created MongoDB user ex09_app: readWrite on ex09
ex09_app can use ex09: OK
ex09_app writing to other_db: refused (Unauthorized)
```

### Redis ACL user (`scripts/setup_redis.py`)

```
ACL SETUSER ex09_app on >*** ~counter:* +@all -@dangerous
whoami: ex09_app
INCR counter:setup_test -> 1
SET other:key 1: refused: this user has no permissions to access one of the keys used as arguments
FLUSHALL: refused: this user has no permissions to run the 'flushall' command
KEYS *: refused: this user has no permissions to run the 'keys' command
```

The Redis user is stricter than the tutorial's: `~counter:*` limits it to the only keys the API needs.

**`ACL SETUSER` is lost when Redis restarts**, because it only changes the running server's memory. To keep it, I would start Redis with an ACL file (in `docker-compose.yml`: `command: redis-server --aclfile /data/users.acl`, with the file on the volume), then run `ACL SAVE` after `ACL SETUSER` so the user is written to that file and loaded again on every start. Another option is to run `scripts/setup_redis.py` every time the stack starts, because it's safe to run again (`reset` and then the same rules).

### The API (`api/app/main.py`)

- `POST /actors` uses a **parameterised query**: `INSERT INTO actor (first_name, last_name) VALUES (%s, %s) RETURNING actor_id`. The values are sent separately from the SQL text, so they can't change the statement. It connects as `ex09_app`, so even a successful injection couldn't drop a table.
- `POST /notes` validates the body with Pydantic in **strict mode** (`StrictInt`, `StrictStr`, `extra="forbid"`). Only an integer and a string can reach `insert_one`, so an object such as `{"$ne": null}` (a MongoDB operator) is rejected with `422` before it touches the database. It connects as the MongoDB user `ex09_app`.
- `POST /counters/{name}` validates `name` against `^[a-z0-9_-]{1,32}$` (a FastAPI `Path` pattern) before building the key `counter:{name}`. A name with `*` or `:` can't create a key outside the `counter:` namespace or act as a pattern. It connects as the Redis user `ex09_app`, which can only touch `counter:*`.

No query is built by concatenating user input.

## Task 4: the API is safe

### SQL injection on `POST /actors`

```
$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/actors -H 'content-type: application/json' -d '{"first_name": "x'); DROP TABLE actor; --", "last_name": "y"}'
{"actor_id":202}
201
```

What was stored (the text is kept exactly as sent, and `actor` still exists):

```
 actor_id |        first_name         | last_name
----------+---------------------------+-----------
      202 | x'); DROP TABLE actor; -- | y

 actors
--------
    202
```

### NoSQL injection on `POST /notes`

A normal note:

```
$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/notes -H 'content-type: application/json' -d '{"customer_id": 1, "text": "Called about a late return"}'
{"id":"6af985563fcf09c9c9a82371"}
201
```

The attack:

```
$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/notes -H 'content-type: application/json' -d '{"customer_id": 1, "text": {"$ne": null}}'
{"detail":[{"type":"string_type","loc":["body","text"],"msg":"Input should be a valid string","input":{"$ne":null}}]}
422
```

Another wrong type (a string instead of an integer) is also rejected:

```
$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/notes -H 'content-type: application/json' -d '{"customer_id": "1", "text": "hi"}'
{"detail":[{"type":"int_type","loc":["body","customer_id"],"msg":"Input should be a valid integer","input":"1"}]}
422
```

What was stored in `ex09.notes` (only the valid note):

```
{'customer_id': 1, 'text': 'Called about a late return'}
```

### Key injection on `POST /counters/{name}`

```
$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/counters/page_views
{"name":"page_views","value":1}
200

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/counters/page_views
{"name":"page_views","value":2}
200

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/counters/a*
{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"a*","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}
422

$ curl -s -w '\n%{http_code}\n' -X POST http://127.0.0.1:8000/counters/x:y
{"detail":[{"type":"string_pattern_mismatch","loc":["path","name"],"msg":"String should match pattern '^[a-z0-9_-]{1,32}$'","input":"x:y","ctx":{"pattern":"^[a-z0-9_-]{1,32}$"}}]}
422
```

What was stored in Redis (`redis-cli --scan --pattern 'counter:*'`): only `counter:page_views` with value `2`.
