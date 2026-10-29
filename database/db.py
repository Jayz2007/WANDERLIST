"""DATABASE LAYER: SQLite connections, transactions, and SQL storage helpers.

Tables: database/schema.sql
Saved data: database/data/workbench.sqlite3 (created automatically)
The backend calls these functions; frontend files never connect to SQLite.
No database server or ORM is required.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import current_app, g


SCHEMA_PATH = Path(__file__).resolve().with_name("schema.sql")


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    """One connection per request, reused until Flask closes that request."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 10000")
    return g.db


def close_db(error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_app(app):
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    app.teardown_appcontext(close_db)
    with app.app_context():
        connection = get_db()
        connection.execute("PRAGMA journal_mode = WAL")
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        connection.commit()


@contextmanager
def transaction():
    """Save the item change and recovery history together, or save neither."""
    connection = get_db()
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def workspace_exists(workspace_id):
    return get_db().execute(
        "SELECT 1 FROM workspaces WHERE id = ?", (workspace_id,)
    ).fetchone() is not None


def create_workspace(workspace_id):
    with transaction() as connection:
        connection.execute(
            "INSERT INTO workspaces (id, created_at) VALUES (?, ?)",
            (workspace_id, timestamp()),
        )
        seed_items(connection, workspace_id)
        log_event(connection, workspace_id, "created", "Your workspace is ready")


def get_workspace(workspace_id):
    return dict(get_db().execute(
        "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
    ).fetchone())


def seed_items(connection, workspace_id):
    """Sample items belong to this browser's workspace only."""
    today = date.today()
    examples = [
        ("Collect a little inspiration", "Save three references and note what makes each one useful.", "Research", "todo", "low", 5),
        ("Sketch the first screen", "A rough sketch is enough. Start with the information people need most.", "Design", "todo", "medium", 3),
        ("Write a short project brief", "Describe who your project is for and the problem it solves.", "Planning", "todo", "high", 1),
        ("Build a first prototype", "Connect a small idea to a working feature. Keep it simple.", "Build", "doing", "high", 2),
        ("Find a visual direction", "Choose a palette, a type style, and a layout that fit your idea.", "Design", "doing", "medium", 4),
        ("Choose a project name", "Give your idea a name you would be happy to put on the front page.", "Planning", "done", "low", 0),
    ]
    now = timestamp()
    for title, description, category, status, priority, days in examples:
        connection.execute(
            """INSERT INTO items
            (workspace_id, title, description, category, status, priority,
             due_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (workspace_id, title, description, category, status, priority,
             (today + timedelta(days=days)).isoformat(), now, now),
        )


def list_items(workspace_id, query="", status="", archived=False):
    sql = "SELECT * FROM items WHERE workspace_id = ? AND archived = ?"
    values = [workspace_id, int(archived)]
    if query:
        literal = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        sql += " AND (title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\')"
        values.extend(["%" + literal + "%"] * 3)
    if status:
        sql += " AND status = ?"
        values.append(status)
    sql += " ORDER BY COALESCE(removed_at, created_at) DESC, id DESC"
    return [dict(row) for row in get_db().execute(sql, values).fetchall()]


def get_item(workspace_id, item_id, archived=None):
    sql = "SELECT * FROM items WHERE id = ? AND workspace_id = ?"
    values = [item_id, workspace_id]
    if archived is not None:
        sql += " AND archived = ?"
        values.append(int(archived))
    row = get_db().execute(sql, values).fetchone()
    return dict(row) if row else None


def stats(workspace_id):
    result = {"total": 0, "todo": 0, "doing": 0, "done": 0, "archived": 0}
    for row in get_db().execute(
        "SELECT status, archived, COUNT(*) AS count FROM items WHERE workspace_id = ? GROUP BY status, archived",
        (workspace_id,),
    ):
        if row["archived"]:
            result["archived"] += row["count"]
        else:
            result[row["status"]] += row["count"]
            result["total"] += row["count"]
    result["open"] = result["todo"] + result["doing"]
    result["progress"] = round(result["done"] / result["total"] * 100) if result["total"] else 0
    return result


def load_history(connection, workspace_id):
    row = connection.execute(
        "SELECT history_json FROM workspaces WHERE id = ?", (workspace_id,)
    ).fetchone()
    values = json.loads(row["history_json"])
    if not isinstance(values, list) or any(type(value) is not int for value in values):
        raise ValueError("Invalid recovery data in the database.")
    return values


def save_history(connection, workspace_id, values):
    connection.execute(
        "UPDATE workspaces SET history_json = ? WHERE id = ?",
        (json.dumps(values), workspace_id),
    )


def log_event(connection, workspace_id, kind, title):
    connection.execute(
        "INSERT INTO events (workspace_id, kind, title, created_at) VALUES (?, ?, ?, ?)",
        (workspace_id, kind, title, timestamp()),
    )


def events(workspace_id, limit=50):
    return [dict(row) for row in get_db().execute(
        "SELECT * FROM events WHERE workspace_id = ? ORDER BY id DESC LIMIT ?",
        (workspace_id, limit),
    ).fetchall()]


# Item/workspace writes live here rather than inside browser route functions.
# The caller supplies an open transaction so item, history, and activity changes
# succeed or roll back together. Do not commit from these individual helpers.

def create_item(connection, workspace_id, values):
    """Insert a validated item and return its database ID."""
    now = timestamp()
    cursor = connection.execute(
        """INSERT INTO items (workspace_id, title, description, category,
        status, priority, due_date, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (workspace_id, values["title"], values["description"], values["category"],
         values["status"], values["priority"], values["due_date"] or None, now, now),
    )
    return cursor.lastrowid


def update_item(connection, workspace_id, item_id, values):
    """Save validated changes to this workspace's active item."""
    connection.execute(
        """UPDATE items SET title=?, description=?, category=?, status=?,
        priority=?, due_date=?, updated_at=? WHERE id=? AND workspace_id=? AND archived=0""",
        (values["title"], values["description"], values["category"], values["status"],
         values["priority"], values["due_date"] or None, timestamp(), item_id, workspace_id),
    )


def move_item(connection, workspace_id, item_id, status):
    """Change the status of an active item."""
    connection.execute(
        "UPDATE items SET status=?, updated_at=? WHERE id=? AND workspace_id=? AND archived=0",
        (status, timestamp(), item_id, workspace_id),
    )


def archive_item(connection, workspace_id, item_id):
    """Mark an item removed without deleting its details."""
    now = timestamp()
    connection.execute(
        "UPDATE items SET archived=1, removed_at=?, updated_at=? WHERE id=? AND workspace_id=?",
        (now, now, item_id, workspace_id),
    )


def restore_item(connection, workspace_id, item_id):
    """Restore the ID chosen by backend/stack.py; SQL does not choose the order."""
    connection.execute(
        "UPDATE items SET archived=0, removed_at=NULL, updated_at=? WHERE id=? AND workspace_id=?",
        (timestamp(), item_id, workspace_id),
    )


def update_workspace(connection, workspace_id, name, accent):
    """Save validated workspace preferences."""
    connection.execute(
        "UPDATE workspaces SET name=?, accent=? WHERE id=?", (name, accent, workspace_id)
    )

def list_destinations(workspace_id, query=""):
    sql = "SELECT * FROM destinations WHERE workspace_id = ?"
    values = [workspace_id]

    if query:
        sql += " AND (country LIKE ? OR notes LIKE ?)"
        values.extend([f"%{query}%", f"%{query}%"])

    sql += " ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, country"
    return [dict(row) for row in get_db().execute(sql, values).fetchall()]


def get_destination(workspace_id, destination_id):
    row = get_db().execute(
        "SELECT * FROM destinations WHERE workspace_id = ? AND id = ?",
        (workspace_id, destination_id),
    ).fetchone()
    return dict(row) if row else None


def save_destination(workspace_id, values):
    now = timestamp()
    with transaction() as connection:
        connection.execute(
            """INSERT INTO destinations
            (workspace_id, country, region, capital, currency, language, flag,
             status, priority, notes, estimated_budget, actual_budget,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id, country) DO UPDATE SET
            region=excluded.region, capital=excluded.capital,
            currency=excluded.currency, language=excluded.language,
            flag=excluded.flag, status=excluded.status,
            priority=excluded.priority, notes=excluded.notes,
            estimated_budget=excluded.estimated_budget,
            actual_budget=excluded.actual_budget, updated_at=excluded.updated_at""",
            (
                workspace_id, values["country"], values.get("region", ""),
                values.get("capital", ""), values.get("currency", ""),
                values.get("language", ""), values.get("flag", ""),
                values.get("status", "wishlist"), values.get("priority", "medium"),
                values.get("notes", ""),
                max(0, float(values.get("estimated_budget") or 0)),
                max(0, float(values.get("actual_budget") or 0)), now, now,
            ),
        )
        log_event(connection, workspace_id, "destination_saved",
                  "Saved destination: " + values["country"])


def delete_destination(workspace_id, destination_id):
    with transaction() as connection:
        connection.execute(
            "DELETE FROM destinations WHERE workspace_id = ? AND id = ?",
            (workspace_id, destination_id),
        )


def travel_stats(workspace_id):
    row = get_db().execute(
        """SELECT COUNT(*) AS total,
        SUM(CASE WHEN status = 'wishlist' THEN 1 ELSE 0 END) AS wishlist,
        SUM(CASE WHEN status = 'planning' THEN 1 ELSE 0 END) AS planning,
        SUM(CASE WHEN status = 'visited' THEN 1 ELSE 0 END) AS visited,
        SUM(estimated_budget) AS estimated_budget,
        SUM(actual_budget) AS actual_budget
        FROM destinations WHERE workspace_id = ?""",
        (workspace_id,),
    ).fetchone()
    return {
        key: row[key] or 0
        for key in ("total", "wishlist", "planning", "visited",
                    "estimated_budget", "actual_budget")
    }


def list_trips(workspace_id):
    return [dict(row) for row in get_db().execute(
        "SELECT * FROM trips WHERE workspace_id = ? ORDER BY start_date, id DESC",
        (workspace_id,),
    ).fetchall()]


def create_trip(workspace_id, values):
    now = timestamp()
    with transaction() as connection:
        cursor = connection.execute(
            """INSERT INTO trips
            (workspace_id, title, notes, start_date, end_date, budget, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (workspace_id, values["title"], values.get("notes", ""),
             values.get("start_date") or None, values.get("end_date") or None,
             max(0, float(values.get("budget") or 0)), now, now),
        )
        trip_id = cursor.lastrowid
        log_event(connection, workspace_id, "trip_created",
                  "Created trip: " + values["title"])
        return trip_id


def get_trip(workspace_id, trip_id):
    row = get_db().execute(
        "SELECT * FROM trips WHERE workspace_id = ? AND id = ?",
        (workspace_id, trip_id),
    ).fetchone()
    return dict(row) if row else None


def list_itinerary(trip_id):
    return [dict(row) for row in get_db().execute(
        """SELECT * FROM itinerary_items WHERE trip_id = ?
        ORDER BY activity_date, start_time, id""",
        (trip_id,),
    ).fetchall()]


def add_itinerary_item(trip_id, values):
    with transaction() as connection:
        connection.execute(
            """INSERT INTO itinerary_items
            (trip_id, destination_id, activity, activity_date, start_time,
             end_time, location, notes, estimated_cost, actual_cost, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trip_id, values.get("destination_id") or None,
                values["activity"], values.get("activity_date") or None,
                values.get("start_time") or None, values.get("end_time") or None,
                values.get("location", ""), values.get("notes", ""),
                max(0, float(values.get("estimated_cost") or 0)),
                max(0, float(values.get("actual_cost") or 0)), timestamp(),
            ),
        )


def delete_itinerary_item(trip_id, item_id):
    with transaction() as connection:
        connection.execute(
            "DELETE FROM itinerary_items WHERE trip_id = ? AND id = ?",
            (trip_id, item_id),
        )
