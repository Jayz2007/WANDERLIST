# BACKEND — what the website does

**Work here for Python behavior, browser routes, input checks, and the Stack.**

| File | Job |
| --- | --- |
| **`stack.py`** | **Student modification zone.** Replace the FIFO recovery buffer with a LIFO Stack. |
| `app.py` | `create_app()`, URL routes, form validation, session/CSRF handling, and recovery flow |
| `config.py` | Absolute paths to the frontend, database file, and private runtime folder |
| `__init__.py` | Marks this folder as a Python package |

Start the whole app from the project root using `START_WEBSITE.bat` or
`python run.py`. After editing Python, stop and restart the server.

## Trace a real feature

`frontend/templates/recovery.html` displays the recovery page. Its form sends
POST `/recovery/restore` to `app.py`. That route rebuilds `HistoryBuffer` from
saved data, calls its `pop()` method, asks `database/db.py` to restore the
chosen item, saves the remaining history, and redirects back to the page.

The SQL queries live in **`../database/db.py`**, not inside this folder.
The page designs live in **`../frontend/`**, not inside this folder.

## Keep the challenge connected

`app.py` and `challenge/check_stack.py` import `HistoryBuffer` from
`backend.stack`. Preserve that public name and its methods, even if your own
implementation uses a differently named class internally. The supplied file is
intentionally FIFO; this reorganization does not provide the LIFO solution.

[Student activity](../docs/STUDENT_ACTIVITY.md) · [Back to the project](../README.md)
