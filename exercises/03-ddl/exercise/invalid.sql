-- Setup (valid rows)
INSERT INTO member (name, email) VALUES ('Ana', 'ana@example.com');
INSERT INTO book (isbn, title) VALUES ('9780306406157', 'Test Book');
INSERT INTO copy (book_id, copy_number, condition) VALUES (1, 1, 'good');
INSERT INTO loan (member_id, copy_id, loan_date, due_date) VALUES (1, 1, '2025-01-01', '2025-01-15');

-- member_email_unique
INSERT INTO member (name, email) VALUES ('Ana 2', 'ana@example.com');

-- due_after_loan
INSERT INTO loan (member_id, copy_id, loan_date, due_date) VALUES (1, 1, '2025-02-01', '2025-01-01');

-- copy_book_number_unique
INSERT INTO copy (book_id, copy_number, condition) VALUES (1, 1, 'good');

-- loan_member_id_fkey
INSERT INTO loan (member_id, copy_id, loan_date, due_date) VALUES (999, 1, '2025-01-01', '2025-01-15');

-- loan_copy_id_fkey (the RESTRICT in action)
DELETE FROM copy WHERE copy_id = 1;