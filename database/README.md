# DATABASE — what the website remembers

**Work here for table definitions, SQL queries, and persistence.**

| Path | Job | Edit by hand? |
| --- | --- | --- |
| `schema.sql` | SQL definitions for `workspaces`, `items`, and `events` | Yes, when designing data changes |
| `db.py` | SQLite connections, transactions, sample data, queries, and storage helpers | Yes, for database behavior |
| `data/workbench.sqlite3` | Actual saved workspaces, items, and events | No text editing; generated at startup |
| `data/.gitkeep` | Keeps the data directory visible in Git | Normally leave it alone |
| `__init__.py` | Makes the database helpers importable | Normally leave it alone |

**The ZIP does not contain a saved database.** `database/data/workbench.sqlite3`
is created automatically when the server first starts. SQLite uses a local
file, so there is no separate database service to install.

## What is stored?

- **workspaces:** browser workspace ID, name, accent, recovery-history ID list.
- **items:** title, description, category, status, priority, due date, archive flag.
- **events:** the saved activity history.

The database remembers the history list; **`backend/stack.py` decides which
history item leaves next**. Do not implement the required LIFO logic by sorting
SQL rows or changing the card display.

## When adding a field

Update the schema/storage queries, backend validation, and frontend form
consistently. Changing `schema.sql` alone does not alter an existing table:
`CREATE TABLE IF NOT EXISTS` only creates missing tables. Back up existing data
and use an explicit migration, or deliberately start a fresh classroom database.

Keep writes inside `db.transaction()` so related item/history/event updates
commit together or roll back together. Queries use parameters rather than
joining user input into SQL strings.

Do not commit local `.sqlite3`, `-wal`, or `-shm` files. Do not delete this
whole folder to reset data: it also contains the schema and Python source.
The private session-signing key is separate: `../instance/.secret_key`.

[Back to the project](../README.md) · [Preserve older data](../docs/REORGANIZATION.md)
