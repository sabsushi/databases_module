import os
from decimal import Decimal

import psycopg
from bson.decimal128 import Decimal128
from psycopg.rows import dict_row
from pymongo import MongoClient, ReplaceOne

DATABASE_URL = os.environ["DATABASE_URL"]
MONGO_URL = os.environ["MONGO_URL"]
BATCH = 5000

FILMS_SQL = """
SELECT f.film_id, f.title, f.release_year::int AS release_year, l.name AS language,
       f.rating::text AS rating, f.length, f.rental_duration, f.rental_rate,
       coalesce((SELECT array_agg(c.name ORDER BY c.name)
                 FROM film_category fc JOIN category c USING (category_id)
                 WHERE fc.film_id = f.film_id), '{}') AS categories,
       coalesce((SELECT json_agg(json_build_object('actor_id', a.actor_id,
                                                   'name', a.first_name || ' ' || a.last_name)
                                 ORDER BY a.actor_id)
                 FROM film_actor fa JOIN actor a USING (actor_id)
                 WHERE fa.film_id = f.film_id), '[]') AS actors
FROM film f JOIN language l ON l.language_id = f.language_id
ORDER BY f.film_id
"""

CUSTOMERS_SQL = """
SELECT c.customer_id, c.first_name, c.last_name, c.email, c.store_id,
       ci.city, co.country,
       (SELECT count(*) FROM rental r WHERE r.customer_id = c.customer_id) AS rental_count
FROM customer c
JOIN address a  ON a.address_id = c.address_id
JOIN city ci    ON ci.city_id = a.city_id
JOIN country co ON co.country_id = ci.country_id
ORDER BY c.customer_id
"""

RECENT_SQL = """
SELECT customer_id, rental_id, film_id, title, rental_date, return_date
FROM (
    SELECT r.customer_id, r.rental_id, i.film_id, f.title, r.rental_date, r.return_date,
           row_number() OVER (PARTITION BY r.customer_id
                              ORDER BY r.rental_date DESC, r.rental_id DESC) AS pos
    FROM rental r
    JOIN inventory i ON i.inventory_id = r.inventory_id
    JOIN film f      ON f.film_id = i.film_id
) x
WHERE pos <= 10
ORDER BY customer_id, pos
"""

RENTALS_SQL = """
SELECT r.rental_id, r.customer_id, i.film_id, f.title,
       coalesce((SELECT array_agg(c.name ORDER BY c.name)
                 FROM film_category fc JOIN category c USING (category_id)
                 WHERE fc.film_id = f.film_id), '{}') AS categories,
       i.store_id, r.rental_date, r.return_date,
       coalesce((SELECT sum(p.amount) FROM payment p WHERE p.rental_id = r.rental_id), 0) AS amount
FROM rental r
JOIN inventory i ON i.inventory_id = r.inventory_id
JOIN film f      ON f.film_id = i.film_id
ORDER BY r.rental_id
"""

def money(value) -> Decimal128:
    return Decimal128(Decimal(value))

def write(collection, docs):
    ops = [ReplaceOne({"_id": d["_id"]}, d, upsert=True) for d in docs]
    total = {"upserted": 0, "modified": 0, "matched": 0}
    for start in range(0, len(ops), BATCH):
        result = collection.bulk_write(ops[start:start + BATCH], ordered=False)
        total["upserted"] += result.upserted_count
        total["modified"] += result.modified_count
        total["matched"] += result.matched_count
    print(f"{collection.name}: {len(docs)} documents "
          f"(upserted {total['upserted']}, matched {total['matched']}, modified {total['modified']}); "
          f"count = {collection.count_documents({})}")

def main():
    mongo = MongoClient(MONGO_URL)
    db = mongo["pagila_docs"]

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as pg:
        films = [
            {
                "_id": r["film_id"],
                "title": r["title"],
                "release_year": r["release_year"],
                "language": r["language"],
                "rating": r["rating"],
                "length": r["length"],
                "rental_duration": r["rental_duration"],
                "rental_rate": money(r["rental_rate"]),
                "categories": list(r["categories"]),
                "actors": r["actors"],
            }
            for r in pg.execute(FILMS_SQL)
        ]

        recent = {}
        for r in pg.execute(RECENT_SQL):
            recent.setdefault(r["customer_id"], []).append({
                "rental_id": r["rental_id"],
                "film_id": r["film_id"],
                "title": r["title"],
                "rental_date": r["rental_date"],
                "return_date": r["return_date"],
            })

        customers = [
            {
                "_id": r["customer_id"],
                "first_name": r["first_name"],
                "last_name": r["last_name"],
                "email": r["email"],
                "store_id": r["store_id"],
                "address": {"city": r["city"], "country": r["country"]},
                "rental_count": r["rental_count"],
                "recent_rentals": recent.get(r["customer_id"], []),
            }
            for r in pg.execute(CUSTOMERS_SQL)
        ]

        rentals = [
            {
                "_id": r["rental_id"],
                "customer_id": r["customer_id"],
                "film_id": r["film_id"],
                "title": r["title"],
                "categories": list(r["categories"]),
                "store_id": r["store_id"],
                "rental_date": r["rental_date"],
                "return_date": r["return_date"],
                "amount": money(r["amount"]),
            }
            for r in pg.execute(RENTALS_SQL)
        ]

    write(db.films, films)
    write(db.customers, customers)
    write(db.rentals, rentals)

if __name__ == "__main__":
    main()
