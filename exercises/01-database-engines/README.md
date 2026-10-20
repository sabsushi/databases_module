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