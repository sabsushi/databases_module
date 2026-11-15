# Exercise 13: MongoDB I, documents, CRUD and validation

| File | Task |
|---|---|
| `load.py`, `pyproject.toml` | 1. Loads Pagila (PostgreSQL) into `pagila_docs`: `films`, `customers`, `rentals` |
| `operations.js` | 2. The 8 operations, for `mongosh` |
| `validation.js` | 3. `$jsonSchema` validation on `films` and the two rejected inserts |
| `index.js` | 4. `explain("executionStats")` before and after the index on `actors.actor_id` |

## How to run

From the repository root:

```bash
bash scripts/create-db.sh ex13 --pagila --reset
```

In `.env`, set `DATABASE_URL=postgresql://postgres:<password>@localhost:5432/ex13` (`MONGO_URL` is the root URL from `.env.example`). From `exercises/13-mongo/exercise/`:

```bash
uv sync
uv run --env-file ../../../.env python load.py
```

The `.js` files run with `mongosh` inside the `mongo` container. Copy them in first (this works in PowerShell and bash):

```bash
docker compose cp exercises/13-mongo/exercise/operations.js mongo:/tmp/operations.js
docker compose cp exercises/13-mongo/exercise/validation.js mongo:/tmp/validation.js
docker compose cp exercises/13-mongo/exercise/index.js mongo:/tmp/index.js
docker compose exec mongo mongosh "mongodb://root:<password>@localhost:27017/pagila_docs?authSource=admin" --quiet --file /tmp/operations.js
docker compose exec mongo mongosh "mongodb://root:<password>@localhost:27017/pagila_docs?authSource=admin" --quiet --file /tmp/validation.js
docker compose exec mongo mongosh "mongodb://root:<password>@localhost:27017/pagila_docs?authSource=admin" --quiet --file /tmp/index.js
```

(Or, with `mongosh` installed locally: `mongosh "<MONGO_URL with /pagila_docs>" --quiet --file operations.js`.) Run `operations.js` on freshly loaded collections: operations 6 to 8 change data.

## Task 1: `load.py`

`load.py` reads Pagila with 4 queries and writes every document with `ReplaceOne({"_id": ...}, doc, upsert=True)` in batches of 5,000. The `_id` is the Pagila ID, so running it again replaces each document with the same content instead of creating a duplicate. Money (`rental_rate`, `amount`) is converted to `Decimal128`. Dates come from psycopg as timezone-aware `datetime` and are stored as BSON dates (UTC).

First run, then second run:

```
films: 1000 documents (upserted 1000, matched 0, modified 0); count = 1000
customers: 999 documents (upserted 999, matched 0, modified 0); count = 999
rentals: 51805 documents (upserted 51805, matched 0, modified 0); count = 51805

films: 1000 documents (upserted 0, matched 1000, modified 0); count = 1000
customers: 999 documents (upserted 0, matched 999, modified 0); count = 999
rentals: 51805 documents (upserted 0, matched 51805, modified 0); count = 51805
```

The second run matched every document and modified none: the documents are identical. Film 1, customer 1 and rental 87420 match the examples of the brief exactly (`categories: ['Games', 'New', 'Travel']`, `rental_count: 66`, `amount: Decimal128('0')`, ...).

### Why this shape

**Actors and categories are embedded in `films`.** A film page always shows its actors and categories, so with them embedded, one read of one document gives everything, with no join. The lists are **small and bounded** (at most 15 actors and 3 categories per film), and they almost never change once the film exists. When an actor's name does change, it's a rare update to the 19–40 films of that actor, which is an acceptable cost for much cheaper reads. Only `actor_id` and `name` are copied, which is what the film page needs. The full actor record would stay in PostgreSQL, the source of truth.

**Only the 10 most recent rentals are embedded in `customers`.** A customer's history **grows without limit** (customer 1 already has 66 rentals, and some have 40+). Embedding all of it would make the document grow forever, get slower to read and write every time, and eventually reach the 16 MB document limit. The customer page only needs the latest few rentals, so a fixed-size window of 10 (kept with `$push` + `$slice`, as in operation 7) gives that view in one read and keeps the document size bounded.

**The full history is in `rentals`.** Every rental is an independent fact that's queried on its own and across customers: reports by category, by month, by store (session 14), a customer's full history with pagination, etc. One document per rental, referencing `customer_id` and `film_id`, keeps documents small and lets those queries use indexes. Each rental also copies the few film fields that reports need (`title`, `categories`), so reports don't need a `$lookup`.

## Task 2: results of `operations.js`

| # | Operation | Expected | Result |
|---|---|---|---|
| 1 | `find({rating: "PG-13", length: {$gt: 120}})` | 118 | **118** |
| 2 | `find({"actors.actor_id": 1})` | 19 | **19** |
| 3 | `find({categories: "Horror", rental_rate: NumberDecimal("0.99")})` | 43 | **43** |
| 4 | `find({recent_rentals: {$elemMatch: {return_date: null}}})` | 56 | **56** |
| 5 | `findOne({_id: 1}, {_id: 0, first_name: 1, last_name: 1, "recent_rentals.title": 1})` | 1 doc, 10 titles | **1 doc, 10 titles** |
| 6 | `updateMany({rating: "NC-17", length: {$lt: 60}}, {$inc: {rental_rate: NumberDecimal("0.50")}})` | 21 modified | **21 modified** |
| 7 | `$push` with `$each`, `$position: 0`, `$slice: 10` on customer 1 | 10 items, new one first | **10 items, rental 99999 first** |
| 8 | `updateOne({_id: 1001}, {$setOnInsert: {title: "TEST FILM"}}, {upsert: true})` twice | 1 upserted, then matched 1 / modified 0 | **as expected** |

Notes:
- **3:** `rental_rate` is `Decimal128`, so it's compared with `NumberDecimal("0.99")`. `categories: "Horror"` matches when the array *contains* "Horror".
- **6:** `$inc` with a `Decimal128` keeps the field as an exact decimal (0.99 + 0.50 = 1.49, with no floating-point error).
- **7:** `$position: 0` puts the new rental first, and `$slice: 10` cuts the array back to 10 in the same atomic update, so the oldest one is dropped.

Full output:

```

=== 1. PG-13 and longer than 120 min: count
118

=== 1. first 3
[
  {
    _id: 33,
    title: 'APOLLO TEEN',
    rating: 'PG-13',
    length: 153
  },
  {
    _id: 35,
    title: 'ARACHNOPHOBIA ROLLERCOASTER',
    rating: 'PG-13',
    length: 147
  },
  {
    _id: 36,
    title: 'ARGONAUTS TOWN',
    rating: 'PG-13',
    length: 127
  }
]

=== 2. films with actor 1: count
19

=== 2. first 3
[
  {
    _id: 1,
    title: 'ACADEMY DINOSAUR'
  },
  {
    _id: 23,
    title: 'ANACONDA CONFESSIONS'
  },
  {
    _id: 25,
    title: 'ANGELS LIFE'
  }
]

=== 3. Horror at 0.99: count
43

=== 3. first 3
[
  {
    _id: 23,
    title: 'ANACONDA CONFESSIONS',
    rental_rate: Decimal128('0.99'),
    categories: [
      'Comedy',
      'Documentary',
      'Horror'
    ]
  },
  {
    _id: 27,
    title: 'ANONYMOUS HUMAN',
    rental_rate: Decimal128('0.99'),
    categories: [
      'Classics',
      'Horror',
      'Travel'
    ]
  },
  {
    _id: 40,
    title: 'ARMY FLINTSTONES',
    rental_rate: Decimal128('0.99'),
    categories: [
      'Horror',
      'Music',
      'Sci-Fi'
    ]
  }
]

=== 4. customers with an open recent rental: count
56

=== 4. first 3
[
  {
    _id: 1,
    first_name: 'MARY',
    last_name: 'SMITH'
  },
  {
    _id: 7,
    first_name: 'MARIA',
    last_name: 'MILLER'
  },
  {
    _id: 8,
    first_name: 'SUSAN',
    last_name: 'WILSON'
  }
]

=== 5. customer 1 (projection)
{
  first_name: 'MARY',
  last_name: 'SMITH',
  recent_rentals: [
    {
      title: 'FELLOWSHIP AUTUMN'
    },
    {
      title: 'FUGITIVE MAGUIRE'
    },
    {
      title: 'CHASING FIGHT'
    },
    {
      title: 'GLEAMING JAWBREAKER'
    },
    {
      title: 'SECRET GROUNDHOG'
    },
    {
      title: 'MULAN MOON'
    },
    {
      title: 'BRAVEHEART HUMAN'
    },
    {
      title: 'SPLENDOR PATTON'
    },
    {
      title: 'DRACULA CRYSTAL'
    },
    {
      title: 'SHAKESPEARE SADDLE'
    }
  ]
}

=== 5. number of titles
10

=== 6. updateMany NC-17 < 60 min
{
  acknowledged: true,
  insertedId: null,
  matchedCount: 21,
  modifiedCount: 21,
  upsertedCount: 0
}

=== 7. $push with $each/$position/$slice
{
  acknowledged: true,
  insertedId: null,
  matchedCount: 1,
  modifiedCount: 1,
  upsertedCount: 0
}

=== 7. recent_rentals size
10

=== 7. first item
{
  rental_id: 99999,
  film_id: 1,
  title: 'ACADEMY DINOSAUR',
  rental_date: ISODate('2026-08-01T10:00:00.000Z'),
  return_date: null
}

=== 7. last item
{
  rental_id: 74068,
  film_id: 249,
  title: 'DRACULA CRYSTAL',
  rental_date: ISODate('2025-02-05T03:06:18.680Z'),
  return_date: ISODate('2025-02-14T02:30:39.441Z')
}

=== 8. first run
{
  acknowledged: true,
  insertedId: 1001,
  matchedCount: 0,
  modifiedCount: 0,
  upsertedCount: 1
}

=== 8. second run
{
  acknowledged: true,
  insertedId: null,
  matchedCount: 1,
  modifiedCount: 0,
  upsertedCount: 0
}

=== 8. the document
{
  _id: 1001,
  title: 'TEST FILM'
}
```

## Task 3: validation

`validation.js` runs `collMod` on `films` with this `$jsonSchema`, `validationLevel: "strict"` and `validationAction: "error"`:

- `title`: `string`
- `rating`: one of `G`, `PG`, `PG-13`, `R`, `NC-17`
- `length`: `int` between 1 and 999
- `rental_rate`: `decimal`
- `categories`: `array` of `string`
- `actors`: `array` of objects with `actor_id` `int` and `name` `string`
- all of the above are `required`

Then it tries to insert two copies of film 1 with one wrong field each:

```
{
  ok: 1
}

=== rating: "XXX"
REJECTED: Document failed validation
[
  {
    operatorName: 'properties',
    propertiesNotSatisfied: [
      {
        propertyName: 'rating',
        details: [
          {
            operatorName: 'enum',
            specifiedAs: {
              enum: [
                'G',
                'PG',
                'PG-13',
                'R',
                'NC-17'
              ]
            },
            reason: 'value was not found in enum',
            consideredValue: 'XXX'
          }
        ]
      }
    ]
  }
]

=== length: "long"
REJECTED: Document failed validation
[
  {
    operatorName: 'properties',
    propertiesNotSatisfied: [
      {
        propertyName: 'length',
        details: [
          {
            operatorName: 'bsonType',
            specifiedAs: {
              bsonType: 'int'
            },
            reason: 'type did not match',
            consideredValue: 'long',
            consideredType: 'string'
          }
        ]
      }
    ]
  }
]
```

Both are rejected, and the details say which rule failed. `load.py` still runs with the validator on, because every document it writes passes the schema (`length` is a Python `int`, stored as BSON `int`; `rental_rate` is `Decimal128`):

```
films: 1000 documents (upserted 0, matched 1000, modified 21); count = 1001
customers: 999 documents (upserted 0, matched 999, modified 1); count = 999
rentals: 51805 documents (upserted 0, matched 51805, modified 0); count = 51805
```

(`modified 21` and `modified 1` are `load.py` putting back the 21 rental rates and customer 1's `recent_rentals` changed by operations 6 and 7. `count = 1001` is because `TEST FILM` from operation 8 is still there.)

## Task 4: index on `actors.actor_id`

```

=== before the index
{
  stages: 'COLLSCAN',
  nReturned: 19,
  totalDocsExamined: 1001,
  totalKeysExamined: 0,
  executionTimeMillis: 2
}

createIndex: actors.actor_id_1

=== after the index
{
  stages: 'FETCH <- IXSCAN (actors.actor_id_1)',
  nReturned: 19,
  totalDocsExamined: 19,
  totalKeysExamined: 19,
  executionTimeMillis: 1
}
```

| | Before | After |
|---|---|---|
| `stage` | `COLLSCAN` | `IXSCAN` (then `FETCH`) |
| `totalDocsExamined` | 1001 (every film) | **19** |
| `nReturned` | 19 | 19 |

Without the index, MongoDB reads every document of the collection to find the 19 films of actor 1. On a freshly loaded collection that's 1,000; here it's 1,001 because of `TEST FILM`. With the index on `actors.actor_id` (a **multikey** index, because `actors` is an array, so each film has one index entry per actor), it jumps directly to the 19 entries for actor 1 and fetches only those 19 documents. The work now depends on the size of the result, not of the collection.
