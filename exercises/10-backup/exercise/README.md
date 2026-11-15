# Exercise 10: Backup and restore

| File | What it is |
|---|---|
| `runbook.md` | **The deliverable**: the runbook for this incident, with every command in order, the row counts of tasks 1, 3 and 5, the real RTO and RPO, how to verify the restore and what I would change |
| `activity.sql` | Normal work after the backup (given by the brief) |
| `disaster.sql` | The incident (given by the brief) |
| `counts.sql` | Row counts of `payment`, `film_actor` and `film_category` |

The dump goes in `backups/` at the repository root, which is in `.gitignore`, so it isn't committed.

Summary:

| | payment | film_actor | film_category |
|---|---|---|---|
| Before the backup | 51,061 | 5,462 | 2,367 |
| After the incident | 45,780 | 4,135 | 2,218 |
| After the restore | 51,061 | 5,462 | 2,367 |

- Restore time (RTO): 0.3 s.
- Data lost (RPO): the 5 payments of `activity.sql` (IDs 102095 to 102099).
