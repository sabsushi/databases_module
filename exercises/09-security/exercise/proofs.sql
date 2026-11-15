SET ROLE ex09_app;
-- Expected: fails
DROP TABLE film;
RESET ROLE;

SET ROLE ex09_app;
-- Expected: works
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
RESET ROLE;

SET ROLE ex09_readonly;
-- Expected: works
SELECT count(*) FROM film;
RESET ROLE;

SET ROLE ex09_readonly;
-- Expected: fails
INSERT INTO actor (first_name, last_name) VALUES ('X', 'Y');
RESET ROLE;

SET ROLE ex09_migrations;
-- Expected: works
CREATE TABLE ex09_default_privileges_test (id int);
RESET ROLE;
SET ROLE ex09_app;
-- Expected: works
INSERT INTO ex09_default_privileges_test VALUES (1);
RESET ROLE;
SET ROLE ex09_migrations;
DROP TABLE ex09_default_privileges_test;
RESET ROLE;

DELETE FROM actor WHERE first_name = 'X' AND last_name = 'Y';
