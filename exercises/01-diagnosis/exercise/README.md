## 1. Docker compose status

![docker compose ps](Deliverable%201.png) 

## 2. Data model

### Tables
- actor
- address
- category
- city
- country
- customer
- film
- film_actor
- film_category
- inventory
- language
- payment (partitioned by month)
- rental
- staff
- store

### Relationships
- address -> city (city_id)
- city -> country (country_id)
- customer -> address (address_id)
- customer -> store (store_id)
- film -> language (language_id)
- film -> language (original_language_id)
- film_actor -> actor (actor_id)
- film_actor -> film (film_id)
- film_category -> category (category_id)
- film_category -> film (film_id)
- inventory -> film (film_id)
- inventory -> store (store_id)
- rental -> customer (customer_id)
- rental -> inventory (inventory_id)
- rental -> staff (staff_id)
- staff -> address (address_id)
- staff -> store (store_id)
- store -> address (address_id)

## 3. Problems

### Problem 1: duplicated data in `customer`
- **File and line:** `.cache/pagila/aeb87bcb0f9751bffb67bd7f4376e8534746d008/pagila-schema.sql`, lines 279 and 282 (`CREATE TABLE public.customer`, starting at line 272)
- **What is wrong:** `activebool boolean NOT NULL DEFAULT true` and `active integer` both store whether the customer is active. `active` is nullable, has no default and no CHECK constraint.
- **Why it matters:** the two columns can disagree (`activebool = true` and `active = 0`), and `active` can hold any number or NULL, so queries can give different answers depending on which column they read.

### Problem 2: a list stored in one column of `film`
- **File and line:** `.cache/pagila/aeb87bcb0f9751bffb67bd7f4376e8534746d008/pagila-schema.sql`, line 451 (`special_features text[]` in `CREATE TABLE public.film`, starting at line 438)
- **What is wrong:** several values (such as "Trailers" or "Deleted Scenes") are packed into one array column instead of living in their own table, linked to `film` by a key.
- **Why it matters:** finding every film with a given feature means searching inside arrays, nothing validates the values (any text is accepted), and a feature's name cannot be changed in one place.

### Problem 3: missing constraints in `film`
- **File and line:** `.cache/pagila/aeb87bcb0f9751bffb67bd7f4376e8534746d008/pagila-schema.sql`, lines 446 to 449 (`rental_rate`, `replacement_cost`, `length` and `rating` in `CREATE TABLE public.film`)
- **What is wrong:** `rental_rate` and `replacement_cost` are `NOT NULL` but have no `CHECK` constraint, so negative or zero prices are accepted. `length` (line 447) is nullable and also has no `CHECK`, so a film can have a negative length.
- **Why it matters:** the database accepts nonsense values, so every application that writes to it has to remember to validate them, and one that forgets will store bad data.