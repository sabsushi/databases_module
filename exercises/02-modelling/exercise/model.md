# Municipal library model

## 1. ER diagram

```mermaid
erDiagram
    PUBLISHER ||--o{ BOOK : publishes
    BOOK ||--|{ BOOK_AUTHOR : "written by"
    AUTHOR ||--o{ BOOK_AUTHOR : writes
    BOOK ||--o{ COPY : has
    READER ||--o{ LOAN : borrows
    COPY ||--o{ LOAN : "is lent in"
    BOOK ||--o{ RESERVATION : "is reserved in"
    READER ||--o{ RESERVATION : makes
    LOAN ||--o{ FINE : "may cause"
```

## 2. Tables (3NF)

| Table | Primary key | Foreign keys |
|---|---|---|
| publisher(name) | publisher_id | |
| author(name) | author_id | |
| book(isbn, title) | book_id | publisher_id |
| book_author | (book_id, author_id) | book_id, author_id |
| copy(barcode) | copy_id | book_id |
| reader(name, email) | reader_id | |
| loan(loan_date, due_date, return_date) | loan_id | copy_id, reader_id |
| reservation(reserved_at) | reservation_id | book_id, reader_id |
| fine(amount, paid) | fine_id | loan_id |

## 3. Denormalisation

I store due_date in loan even though it can be calculated.
Reason: if the loan period changes later, old loans keep their original due date.