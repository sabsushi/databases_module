CREATE TABLE member (
    member_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name      text NOT NULL,
    email     text NOT NULL,
    joined_at date NOT NULL DEFAULT current_date,
    CONSTRAINT member_email_unique UNIQUE (email)
);

CREATE TABLE book (
    book_id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn    text NOT NULL,
    title   text NOT NULL,
    CONSTRAINT book_isbn_unique UNIQUE (isbn)
);

CREATE TABLE copy (
    copy_id     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- CASCADE: a copy means nothing without its book
    book_id     integer NOT NULL REFERENCES book ON DELETE CASCADE,
    copy_number integer NOT NULL,
    condition   text NOT NULL,
    CONSTRAINT copy_condition_valid CHECK (condition IN ('new', 'good', 'worn', 'damaged')),
    CONSTRAINT copy_book_number_unique UNIQUE (book_id, copy_number)
);

CREATE TABLE loan (
    loan_id   integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    -- RESTRICT: a member or copy with loan history must not be deleted by accident
    member_id integer NOT NULL REFERENCES member ON DELETE RESTRICT,
    copy_id   integer NOT NULL REFERENCES copy ON DELETE RESTRICT,
    loan_date date NOT NULL DEFAULT current_date,
    due_date  date NOT NULL,
    fine      numeric(8,2) NOT NULL DEFAULT 0,
    CONSTRAINT due_after_loan CHECK (due_date > loan_date),
    CONSTRAINT fine_not_negative CHECK (fine >= 0)
);