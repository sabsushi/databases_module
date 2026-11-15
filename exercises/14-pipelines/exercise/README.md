# Exercise 14: MongoDB II, aggregation pipelines and reports

| File | Task |
|---|---|
| `pipelines.js` | 1 to 4. The four pipelines, for `mongosh` |
| `backup_mongo.sh` | 5. Dumps `pagila_docs` to `backups/` as a compressed, dated archive |
| `restore_mongo.sh` | 5. Restores the latest archive into `pagila_docs_restored` and compares the counts |

## How to run

The collections must be freshly loaded by exercise 13's `load.py` and not changed afterwards (operations 6 to 8 of exercise 13 change them). If they were changed, drop and reload:

```bash
docker compose exec mongo mongosh "mongodb://root:<password>@localhost:27017/pagila_docs?authSource=admin" --quiet --eval "db.dropDatabase()"
cd exercises/13-mongo/exercise && uv run --env-file ../../../.env python load.py && cd ../../..
```

Pipelines (from the repository root):

```bash
docker compose cp exercises/14-pipelines/exercise/pipelines.js mongo:/tmp/pipelines.js
docker compose exec mongo mongosh "mongodb://root:<password>@localhost:27017/pagila_docs?authSource=admin" --quiet --file /tmp/pipelines.js
```

Backup and restore (bash or Git Bash, from the repository root; they read `MONGO_ROOT_USER` and `MONGO_ROOT_PASSWORD` from `.env` and run `mongodump`, `mongorestore` and `mongosh` inside the `mongo` container):

```bash
bash exercises/14-pipelines/exercise/backup_mongo.sh
bash exercises/14-pipelines/exercise/restore_mongo.sh
```

`backups/` is in `.gitignore`, so the archives are never committed.

## Task 1: revenue per category per month in 2025

`$match` on `rental_date` in 2025 → `$unwind: "$categories"` (a rental counts in each category of its film) → `$group` by category and `$dateTrunc` of `rental_date` to the month, `$sum` of `amount` → `$project` → `$sort` by category and month.

**192 documents.** First 3:

```
[
  {
    revenue: Decimal128('333.87'),
    category: 'Action',
    month: ISODate('2025-01-01T00:00:00.000Z')
  },
  {
    revenue: Decimal128('342.98'),
    category: 'Action',
    month: ISODate('2025-02-01T00:00:00.000Z')
  },
  {
    revenue: Decimal128('385.83'),
    category: 'Action',
    month: ISODate('2025-03-01T00:00:00.000Z')
  }
]

```

Action, January 2025: **333.87**

```
[
  {
    revenue: Decimal128('333.87'),
    category: 'Action',
    month: ISODate('2025-01-01T00:00:00.000Z')
  }
]
```

### Why 333.87 and not 314.94 (exercise 05, question 2)

The two reports answer slightly different questions:

- **Exercise 05** grouped **payments** by **`payment_date`**: "money received in January 2025 for Action films".
- **This pipeline** groups **rentals** by **`rental_date`**, and each rental's `amount` is the sum of *all* its payments, whatever their date: "money from the Action rentals made in January 2025".

A rental and its payment don't always fall in the same month. A film rented at the end of December can be paid in January (it counts in January in exercise 05, but in December here), and a film rented in January can be paid in February (it counts in January here, but in February in exercise 05). I checked it in PostgreSQL for Action:

| | Amount |
|---|---|
| Exercise 05: payments dated January 2025 | 314.94 |
| − payments dated January 2025 for rentals made in another month | −27.90 |
| + payments dated in another month for rentals made in January 2025 | +46.83 |
| **= this pipeline: rentals made in January 2025** | **333.87** |

The MongoDB document doesn't keep the payment dates (only the total `amount`), so this collection can't reproduce the report by payment date. To get both, `rentals` would need to embed the payments (with their dates), or the report by payment date stays in PostgreSQL.

## Task 2: the actor with most films in each category, with ties

`$unwind` categories and actors → `$group` by (category, actor) to count films → `$group` by category with `$max` of the count and `$push` of every actor → `$filter` the actors whose count equals the maximum (so ties are kept) → `$sortArray` by `actor_id`.

**16 documents with 30 actors in total.** First 3:

```
[
  {
    films: 10,
    category: 'Action',
    actors: [
      {
        actor_id: 65,
        name: 'ANGELA HUDSON'
      },
      {
        actor_id: 181,
        name: 'MATTHEW CARREY'
      }
    ]
  },
  {
    films: 10,
    category: 'Animation',
    actors: [
      {
        actor_id: 13,
        name: 'UMA WOOD'
      },
      {
        actor_id: 150,
        name: 'JAYNE NOLTE'
      }
    ]
  },
  {
    films: 9,
    category: 'Children',
    actors: [
      {
        actor_id: 105,
        name: 'SIDNEY CROWE'
      },
      {
        actor_id: 133,
        name: 'RICHARD PENN'
      },
      {
        actor_id: 139,
        name: 'EWAN GOODING'
      }
    ]
  }
]
total actors: 30
```

## Task 3: distribution of film lengths

`$bucket` with `groupBy: "$length"` and `boundaries: [0, 60, 90, 120, 150, 186]`. Each bucket includes its lower boundary and excludes the upper one, so `186` is needed to include the films of 185 minutes.

**5 documents**: 96, 224, 214, 216 and 250, as expected.

```
[
  {
    _id: 0,
    films: 96
  },
  {
    _id: 60,
    films: 224
  },
  {
    _id: 90,
    films: 214
  },
  {
    _id: 120,
    films: 216
  },
  {
    _id: 150,
    films: 250
  }
]
```

## Task 4: `$facet`

One pass over `films` with three sub-pipelines: `totals` (`$group` with `$sum` and `$avg`, rounded to 2 decimals), `by_rating` (`$group` by rating) and `longest` (`$sort` by `length` descending and `title` ascending to break ties, `$limit: 5`).

**1 document**: 1,000 films, average rate 2.98; G 178, PG 194, PG-13 223, R 195, NC-17 210; the 5 longest are CHICAGO NORTH, CONTROL ANTHEM, DARN FORRESTER, GANGS PRIDE and HOME PITY, all 185 minutes.

```
[
  {
    totals: [
      {
        films: 1000,
        avg_rental_rate: Decimal128('2.98')
      }
    ],
    by_rating: [
      {
        films: 178,
        rating: 'G'
      },
      {
        films: 210,
        rating: 'NC-17'
      },
      {
        films: 194,
        rating: 'PG'
      },
      {
        films: 223,
        rating: 'PG-13'
      },
      {
        films: 195,
        rating: 'R'
      }
    ],
    longest: [
      {
        title: 'CHICAGO NORTH',
        length: 185
      },
      {
        title: 'CONTROL ANTHEM',
        length: 185
      },
      {
        title: 'DARN FORRESTER',
        length: 185
      },
      {
        title: 'GANGS PRIDE',
        length: 185
      },
      {
        title: 'HOME PITY',
        length: 185
      }
    ]
  }
]
```

## Task 5: backup and restore

`backup_mongo.sh` runs `mongodump --db pagila_docs --archive --gzip` and writes the archive to `backups/pagila_docs_<date>_<time>.archive.gz`:

```
Backup written to backups/pagila_docs_2026-11-15_102625.archive.gz (2.2M)
```

`restore_mongo.sh` takes the newest archive in `backups/` and runs `mongorestore --archive --gzip --drop --nsFrom 'pagila_docs.*' --nsTo 'pagila_docs_restored.*'`. That restores every collection under the new database name, so the original is never touched, and `--drop` replaces a previous restore. Then it compares the document counts of the two databases.

Output of `restore_mongo.sh`:

```
Restoring backups/pagila_docs_2026-11-15_102625.archive.gz into pagila_docs_restored
finished restoring pagila_docs_restored.films (1000 documents, 0 failures)
finished restoring pagila_docs_restored.customers (999 documents, 0 failures)
finished restoring pagila_docs_restored.rentals (51805 documents, 0 failures)
53804 document(s) restored successfully. 0 document(s) failed to restore.
collection       pagila_docs  pagila_docs_restored
customers                999                   999
films                   1000                  1000
rentals                51805                 51805
OK: every collection has the same number of documents
```
