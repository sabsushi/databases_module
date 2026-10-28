docker compose exec -T postgres createdb -U postgres library
Get-Content exercises/03-ddl/schema.sql | docker compose exec -T postgres psql -U postgres -d library -v ON_ERROR_STOP=1
Get-Content exercises/03-ddl/invalid.sql | docker compose exec -T postgres psql -U postgres -d library
