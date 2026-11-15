# Exercise 1: Database engines and diagnosis

Files: `README.md` (this file, with the answers to tasks 2 to 5), `shop.json` (the shop's data file, exactly as given, so the line numbers below match) and `Deliverable 1.png` (the screenshot of task 1).

## 1. Docker compose status

![docker compose ps](Deliverable%201.png)

The three services (`postgres`, `mongo`, `redis`) are `healthy`.

## 2. Data model of `shop.json`

### Entities and fields

| Entity | Fields | Lines |
|---|---|---|
| **Customer** | `id`, `name`, `email`, `city` | 2–5 |
| **Order** | `id`, `customer_id`, `customer_name`, `customer_email`, `items`, `total`, `date` | 6–13 |
| **Product** | `name`, `price`, `stock` | 14–17 |

There is also a fourth entity hidden inside a field: the **order line** (a product and a quantity, for example `Mouse x2`). It has no structure of its own, because all the lines of an order are written as one string in `items`.

### Relationships

- **Customer 1 — N Order**: an order belongs to one customer through `customer_id`, and a customer can have many orders. The order also copies the customer's `name` and `email`.
- **Order N — N Product**: an order contains several products, and a product appears in many orders, each time with a quantity. This relationship is only stored as text in `items` (`"Keyboard x1; Mouse x2"`), and it refers to products by **name**, because products have no `id`.

Nothing in the file enforces any of these relationships: they exist only because the application reads the values that way.

## 3. Problems in `shop.json`

| # | Line | Kind of problem | What is wrong | What can go wrong |
|---|---|---|---|---|
| 1 | 7 | Duplicated data | The order copies `customer_name` and `customer_email` from the customer of line 3. | When Ana changes her email, every order has to be updated too. Any copy that is missed contradicts the customer record. |
| 2 | 11 | Duplicated data (already inconsistent) | Order 2 of Ana has `customer_email` `ana.silva@example.com`, but her customer record (line 3) and order 1 (line 7) say `ana@example.com`. | Problem 1 has already happened: nobody knows which email is right, and a confirmation email can go to the wrong address. |
| 3 | 9 | Missing integrity rule (reference) | `customer_id: 3` doesn't exist in `customers` (only 1 and 2). "Marta Reis" only exists inside this order. | An order with no customer: it can't be shown in any customer's history, and the shop has no record of who Marta is. |
| 4 | 9 and 11 | Missing integrity rule (unique key) | Two different orders both have `id: 2`. | "Open order 2" is ambiguous: an update or a refund can be applied to the wrong order. This is what happens when two requests compute `max(id) + 1` at the same time (task 4). |
| 5 | 8 | A list stored in a single field | `items` is one string with a home-made format: `"Keyboard x1; Mouse x2"`. | To answer "how many mice were sold?", every string has to be split and parsed. A typo (`"Mouse  x 2"`) breaks the parser, and a product name containing `;` or ` x` breaks the format. |
| 6 | 8, 10, 12 | Wrong type | `total` is a string in line 8 (`"59.90"`), a string that isn't a number in line 10 (`"abc"`), and a number in line 12 (`12.5`). | Adding up the totals fails or gives a wrong result (in JavaScript, `"59.90" + 12.5` is `"59.9012.5"`). `"abc"` makes any revenue report crash. |
| 7 | 8 and 10 | Inconsistent format | `date` is `"07/10/2026"` in line 8 and `"2026-10-08"` in line 10. | Dates can't be sorted or compared as text, and `07/10/2026` is ambiguous: 7 October (Portugal) or 10 July (USA)? |
| 8 | 12 | Missing integrity rule (check) | Quantity `x-1`: a negative quantity. | An order that gives the customer money back or *adds* stock, and a total (12.5) that doesn't match the product's price (15). |
| 9 | 16 | Missing integrity rule (check) | `stock: -2`. | The shop has sold 2 mice it didn't have. Nothing stopped the sale because nothing checks that stock stays at 0 or above. |
| 10 | 16 | Wrong type | `price: "15"` is a string, while the price in line 15 is a number (`29.90`). | `price * quantity` gives different results depending on the language, and sorting by price sorts as text (`"15"` comes before `"9"`). |
| 11 | 9 | Missing integrity rule (format) | `customer_email: "marta@example"` isn't a valid email (no domain). | Order emails to this customer fail without anyone noticing. |
| 12 | 15–16 (and 8, 10, 12) | Missing key | Products have no `id`, and orders refer to them by `name`. | Renaming "Mouse" to "Wireless Mouse" breaks every past order that mentions it, and two products can't have the same name. |

That's 12 problems of 6 kinds: duplicated data, missing integrity rules (reference, unique key, checks, format), a list stored in a single field, wrong type, inconsistent format and a missing key.

## 4. What happens with 100,000 orders, and with two requests at the same time

The application reads the **whole file**, changes it in memory and writes the **whole file** back on every request.

**Finding the orders of one customer.** With 100,000 orders, the file is about 20 MB (around 200 bytes per order). To find Ana's 5 orders, the application reads and parses all 20 MB and then checks all 100,000 orders one by one, because there is no index: the cost grows with the size of the file, not with the size of the answer. The whole file is also in memory during each request, so 50 requests at once use about 1 GB.

**Adding one order.** Adding one order of 200 bytes means reading 20 MB, parsing it, adding the order, serialising 20 MB again and writing 20 MB to disk. Each new order makes every later write a little slower. If the process crashes or the disk fills up in the middle of the write, the file is left half-written, and **all** the data (not just the new order) is lost or corrupted, because the old content was being overwritten.

**Two requests adding an order at the same time.** The read-modify-write isn't atomic, and nothing stops two requests from interleaving:

| Step | Request A | Request B |
|---|---|---|
| 1 | reads the file (100,000 orders) | |
| 2 | | reads the file (100,000 orders) |
| 3 | adds order 100,001 in memory | |
| 4 | | adds its order in memory, also with id 100,001 (it also computes `max(id) + 1`) |
| 5 | writes the file (A's order is there) | |
| 6 | | writes the file: **overwrites A's write** |

The result is a **lost update**: A's order disappears, even though A told its customer that the order was accepted. Both requests also gave their order the same `id`, which is how line 11 got a duplicate `id: 2`. And if B reads while A is still writing, B reads half a file, which isn't valid JSON, and fails or saves a broken file. The more traffic there is, the more often this happens.

A database engine avoids all of this: an index finds a customer's orders without reading everything, an `INSERT` writes only the new row, a sequence gives every order a unique id even under concurrency, transactions make each write atomic, and the write-ahead log means a crash never leaves the data half-written.

## 5. Which engine for each kind of data

| Data | Engine | Why |
|---|---|---|
| **Customers** | **PostgreSQL** | Domain data that must never be lost or contradict itself: a `UNIQUE` email, a `CHECK` on its format, `NOT NULL` fields, and the customer is the target of a foreign key from orders. Each customer is stored once, so problems 1, 2 and 3 can't happen. |
| **Orders** | **PostgreSQL** | Orders are money, so they need **ACID transactions**: creating an order, inserting its lines and decreasing the stock must happen all together or not at all. Order lines become their own table (`order_item`, with a foreign key to `product` and `CHECK (quantity > 0)`), the total is a `numeric(10,2)`, and the date is a `timestamptz`. A primary key from a sequence gives each order a unique id, and the engine's concurrency control prevents lost updates. |
| **Products** | **PostgreSQL** | Price and stock are changed by orders in the same transaction, so they have to live in the same engine as orders. `CHECK (stock >= 0)` makes problem 9 impossible, `price numeric(10,2) CHECK (price > 0)` fixes problem 10, and a `product_id` key fixes problem 12. (If the catalogue later had very different attributes per product, those descriptions could be copied to MongoDB for reading, but price and stock would stay in PostgreSQL.) |
| **Last 10 products a customer viewed** | **Redis** | Small, changes on every page view, and only needs to be read quickly. A Redis **list** per customer: `LPUSH customer:{id}:viewed {product_id}` followed by `LTRIM customer:{id}:viewed 0 9` keeps exactly the last 10, in memory, at very little cost per view. `EXPIRE` can delete it after a few weeks without visits. If it's lost, nothing important is lost: it fills again as the customer browses. |
| **Number of times each product page was opened today** | **Redis** | A counter that changes many times per second. `INCR product:{id}:views:{date}` is atomic in Redis, so concurrent visits are never lost (unlike the file, task 4), and it runs in memory without a disk write per visit. `EXPIRE` removes old days automatically. A sorted set (`ZINCRBY views:{date} 1 {product_id}`) also gives the most viewed products of the day directly. If an exact daily total is needed for a report, it can be copied to PostgreSQL once a day. |
