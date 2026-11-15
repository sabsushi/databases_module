DROP TABLE IF EXISTS book;
DROP DOMAIN IF EXISTS isbn13;
DROP FUNCTION IF EXISTS is_valid_isbn13(text);

CREATE FUNCTION is_valid_isbn13(value text) RETURNS boolean
LANGUAGE sql
IMMUTABLE STRICT PARALLEL SAFE
RETURN
    value ~ '^[0-9](-?[0-9])*$'
    AND length(replace(value, '-', '')) = 13
    AND (
        SELECT (10 - sum(substr(d, i, 1)::int * CASE WHEN i % 2 = 1 THEN 1 ELSE 3 END) % 10) % 10
        FROM (SELECT replace(value, '-', '') AS d) digits,
             generate_series(1, 12) AS i
        GROUP BY d
    ) = substr(replace(value, '-', ''), 13, 1)::int;

CREATE DOMAIN isbn13 AS text CHECK (is_valid_isbn13(VALUE));

CREATE TABLE book (
    book_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn    isbn13 NOT NULL UNIQUE,
    title   text NOT NULL
);

INSERT INTO book (isbn, title) VALUES ('978-0-306-40615-7', 'Valid with hyphens');
INSERT INTO book (isbn, title) VALUES ('9781402894626', 'Valid without hyphens');
INSERT INTO book (isbn, title) VALUES ('978-3-16-148410-0', 'Valid, check digit 0');

INSERT INTO book (isbn, title) VALUES ('978-0-306-40615-8', 'Wrong check digit');
INSERT INTO book (isbn, title) VALUES ('978-0-306-4061', 'Too short');
INSERT INTO book (isbn, title) VALUES ('-9780306406157', 'Leading hyphen');
INSERT INTO book (isbn, title) VALUES ('978--0306406157', 'Two hyphens in a row');

SELECT book_id, isbn, title FROM book ORDER BY book_id;
