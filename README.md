# Workbench — Full-Stack Student Starter

**Frontend = what students see. Backend = what the website does. Database = what it remembers.**

This is the same remixable classroom website, reorganized so each part is easy
to find. It uses Python + Flask + Jinja + HTML/CSS + SQLite. There is **one project
and one server**; no Node.js build, separate frontend install, database server,
account, or API key is required.

> **Student DSA file: [`backend/stack.py`](backend/stack.py).** The recovery buffer
> is still deliberately **FIFO**. Turning it into a **LIFO Stack** is the activity,
> not a completed answer included in this starter.

## 1. Know where to work

| Folder | What it contains | Start here |
| --- | --- | --- |
| **[`frontend/`](frontend/README.md)** | Pages, styling, and icons | `frontend/templates/index.html` and `frontend/static/style.css` |
| **[`backend/`](backend/README.md)** | Python routes, validation, and recovery logic | `backend/app.py` and **`backend/stack.py`** |
| **[`database/`](database/README.md)** | SQLite queries, table definitions, and saved data | `database/db.py`, `database/schema.sql`, `database/data/` |
| [`docs/`](docs/README.md) | Student activity, teacher guide, and navigation help | `docs/REPOSITORY_MAP.md` |
| [`tests/`](tests/README.md) | Checks that the website and folder wiring work | Run `RUN_TESTS.bat` |
| [`challenge/`](challenge/README.md) | Separate LIFO goal checks | Run `CHECK_STACK.bat` |

```text
Workbench_Starter/
|
+-- frontend/                    WHAT YOU SEE
|   +-- README.md
|   +-- templates/               HTML + Jinja pages
|   |   +-- base.html            Shared page layout and navigation
|   |   +-- index.html           Main board/list page
|   |   +-- item_form.html       Add/edit form
|   |   +-- recovery.html        Removed items and restore button
|   |   +-- activity.html        Activity page
|   |   +-- settings.html        Workspace settings
|   |   +-- guide.html           Student guide and project map
|   |   +-- error.html           Friendly error page
|   |   +-- macros.html          Reusable template pieces/icons
|   +-- static/
|       +-- style.css            Colors, layout, and responsive styles
|       +-- favicon.svg          Browser tab icon
|
+-- backend/                     WHAT THE WEBSITE DOES
|   +-- README.md
|   +-- __init__.py              Makes this a Python package
|   +-- app.py                   Flask routes and validation
|   +-- config.py                Paths connecting the three layers
|   +-- stack.py                 STUDENT STACK CHALLENGE
|
+-- database/                    WHAT THE WEBSITE REMEMBERS
|   +-- README.md
|   +-- __init__.py
|   +-- db.py                    SQLite connection, queries, transactions
|   +-- schema.sql               Definitions of the three tables
|   +-- data/
|       +-- .gitkeep             Keeps this empty folder in Git
|       +-- workbench.sqlite3    Generated at first startup; not shipped
|
+-- docs/                        Guides and activity instructions
+-- tests/                       Website and folder-layout checks
+-- challenge/                   LIFO acceptance checks
|
+-- START_HERE.txt               Beginner setup and folder map
+-- SETUP_WINDOWS.bat            First-time Windows setup
+-- START_WEBSITE.bat            Start the whole website
+-- RUN_TESTS.bat                Check website/layout behavior
+-- CHECK_STACK.bat              Check the student's LIFO goal
+-- run.py                       Cross-platform Python launcher
+-- setup.sh / start.sh          macOS/Linux launchers
+-- requirements.txt             Python dependencies
+-- .gitignore                   Excludes local data, keys, and caches
+-- .gitattributes               Consistent text-file line endings
```

The `.venv/` environment and `instance/.secret_key` appear locally when needed.
They are generated support files, **not extra application layers**. Do not edit
or upload them. The actual SQLite database belongs in **`database/data/`**.

For a file-by-file tour and an old-to-new path map, read
[`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md).

## 2. Run on Windows

Install Python **3.10 or newer**, with **Add Python to PATH** enabled. Extract
all the files into a **new folder**; do not run from inside the ZIP viewer.
Open `Workbench_Starter` and run:

```powershell
.\SETUP_WINDOWS.bat
.\START_WEBSITE.bat
```

Double-clicking these files also works. First-time setup needs internet for
Flask. On later runs, only `START_WEBSITE.bat` is needed.

The browser opens at **http://127.0.0.1:5000**. Keep the terminal open while
using the website. Press **Ctrl+C** there to stop it.

**Do not run `backend/app.py` directly or open the HTML files by double-clicking.**
Use the launcher so imports, Jinja templates, and database access work together.

### Manual PowerShell setup

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

If `py` is unavailable, use `python` instead of `py -3`. There is no need to
activate the environment or change PowerShell's execution policy.

### macOS / Linux

```bash
sh setup.sh
sh start.sh
```

### Another port

```powershell
.\START_WEBSITE.bat --port 5001
```

## 3. How the layers connect

```text
Browser
   | submits an HTML form
   v
frontend/templates/     <-- page layout, form fields, and buttons
   |
   v
backend/app.py          <-- handles the URL and checks the input
   |                 \
   |                  --> backend/stack.py (recovery behavior)
   v
database/db.py          <-- executes SQL inside a transaction
   |
   v
database/data/workbench.sqlite3
   |
   +--> backend renders a frontend template --> browser shows the result
```

`database/schema.sql` defines the tables. The app applies it automatically at
startup. Frontend files do **not** connect directly to the database.

## 4. What already works

Create and edit items; set categories, priorities, dates, and statuses; move
between To do/In progress/Done; switch board/list views; search and filter;
remove and restore items; view activity; customize the workspace name and
accent. The original responsive design is preserved.

Each browser profile has its own local workspace. Tabs in the same profile
share it; another browser/private session gets a different workspace. This is
a classroom sandbox, not an account/login system. Saved data persists across
refreshes and restarts when the browser cookie, database, and signing key remain.

## 5. The Stack activity is intentionally unfinished

Edit **[`backend/stack.py`](backend/stack.py)**. The provided `HistoryBuffer`
stores item IDs in a dictionary and takes the oldest first (FIFO). Students
must replace its representation and operations with a real LIFO Stack.

Removing A, B, then C currently restores A first. The required goal is C, B, A.
Keep the public methods and the oldest/bottom-to-newest/top `to_list()` storage
contract. The real routes still use this class; changing only visible card
order is not a solution.

See [`docs/STUDENT_ACTIVITY.md`](docs/STUDENT_ACTIVITY.md) for the full task.

## 6. Two different checks

```powershell
.\RUN_TESTS.bat
.\CHECK_STACK.bat
```

**RUN_TESTS** checks the supplied website and layout. It is designed to pass
both before and after the student's Stack implementation.

**CHECK_STACK** checks the LIFO goal. Its failures are expected while the
starter remains FIFO; they are not installation failures.

Equivalent commands from the project root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe challenge\check_stack.py
```

For the validation status of this delivery, see
[`docs/VALIDATION.md`](docs/VALIDATION.md). The structural checks were run;
Flask integration testing was blocked by package-download access in the build
environment, so run `RUN_TESTS.bat` after setup on your machine.

## 7. Editing and troubleshooting

Open the **whole `Workbench_Starter` folder** in VS Code, not only one layer.
After editing HTML or CSS, save and refresh (Ctrl+F5 for cached CSS). After
editing Python, stop and restart the server. Keep all three folders together.

For optional local Python auto-reload, run from the project root:

```powershell
.\.venv\Scripts\python.exe -m flask --app backend.app run --debug
```

| Problem | What to check |
| --- | --- |
| Python/Flask missing | Run first-time setup; use the `.venv` interpreter. |
| Port already in use | Stop the old server or use `--port 5001`. |
| Module not found | Start with root `run.py`/`START_WEBSITE.bat`, not a file inside `backend/`. |
| Template not found | Keep `frontend/templates/` beside `backend/`; check `backend/config.py`. |
| Form expired | Reload the page and submit again; cookies must be enabled. |
| Python changes not visible | Stop/restart the server. |
| Stack checks fail | Expected until `backend/stack.py` implements the LIFO goal. |
| Changed schema but old table stayed the same | `CREATE TABLE IF NOT EXISTS` does not migrate existing columns. Back up data and plan an explicit migration. |

For a fresh demo, use a private browser window. To reset **all local saved data**,
stop the server and back up then delete only the generated `workbench.sqlite3`
and any matching `-wal`/`-shm` files in `database/data/`, plus `instance/.secret_key`
(or the generated `instance/` folder). **Never delete `database/` itself**; it
contains your source code and schema. Restart to create fresh data.

Keeping a previous installation's saved data? Follow
[`docs/REORGANIZATION.md`](docs/REORGANIZATION.md) before deleting anything.

## 8. GitHub submission

Commit `frontend/`, `backend/`, `database/db.py`, `database/schema.sql`, the
`.gitkeep`, docs, tests, challenge checks, root launchers, and `requirements.txt`.
Do **not** commit `.venv/`, `instance/`, a local `.secret_key`, or generated
SQLite files. The `.gitignore` already excludes them. Manual browser uploads
must exclude them too.

This starter listens on `127.0.0.1` for local use. Public hosting is not required.

## Reference documentation

- Flask application paths: https://flask.palletsprojects.com/en/stable/api/
- Flask quickstart: https://flask.palletsprojects.com/en/stable/quickstart/
- Flask + SQLite: https://flask.palletsprojects.com/en/stable/tutorial/database/
- Python stacks: https://docs.python.org/3/tutorial/datastructures.html#using-lists-as-stacks
