"""BACKEND: Workbench browser routes, input validation, and feature logic.

A form in frontend/templates/ sends a request to a route in this file.
The route calls backend/stack.py for recovery behavior and database/db.py
for storage, then renders another frontend template.

Start the website with run.py or START_WEBSITE.bat from the project root.
"""

import hmac
import os
import secrets
from datetime import date, datetime
from pathlib import Path

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for

from database import db
from backend.stack import HistoryBuffer
from backend.config import DATABASE_PATH, FRONTEND_DIR, INSTANCE_DIR


STATUSES = {"todo": "To do", "doing": "In progress", "done": "Done"}
PRIORITIES = {"low": "Low", "medium": "Medium", "high": "High"}
ACCENTS = {"pine": "Pine green", "blue": "Ocean blue", "plum": "Soft plum", "clay": "Warm clay"}


def create_app(test_config=None):
    # Physical folders are separate; the browser still uses the same URLs.
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR / "templates"),
        static_folder=str(FRONTEND_DIR / "static"),
        static_url_path="/static",
        instance_path=str(INSTANCE_DIR),
        instance_relative_config=True,
    )
    app.config.from_mapping(
        DATABASE=str(DATABASE_PATH),
        MAX_CONTENT_LENGTH=64 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        TEMPLATES_AUTO_RELOAD=True,
        SEND_FILE_MAX_AGE_DEFAULT=0,
        TESTING=False,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or local_secret(app.instance_path)
    db.init_app(app)

    @app.before_request
    def prepare_request():
        if request.endpoint in {"static", "health"}:
            return
        if request.method == "POST":
            expected = session.get("csrf_token", "")
            received = request.form.get("csrf_token", "")
            if not expected or not hmac.compare_digest(expected.encode(), received.encode()):
                abort(400, description="This form expired. Reload the page and try again.")
        session.setdefault("csrf_token", secrets.token_hex(24))
        workspace_id = session.get("workspace_id")
        if not isinstance(workspace_id, str) or not db.workspace_exists(workspace_id):
            workspace_id = secrets.token_hex(16)
            db.create_workspace(workspace_id)
            session["workspace_id"] = workspace_id
        g.workspace_id = workspace_id

    @app.context_processor
    def template_helpers():
        if not hasattr(g, "workspace_id"):
            return {"workspace": {"name": "My workspace", "accent": "pine"},
                    "counts": {"total": 0, "archived": 0},
                    "csrf_token": session.get("csrf_token", ""),
                    "statuses": STATUSES, "priorities": PRIORITIES, "accents": ACCENTS}
        return {
            "workspace": db.get_workspace(g.workspace_id),
            "counts": db.stats(g.workspace_id),
            "csrf_token": session["csrf_token"],
            "statuses": STATUSES,
            "priorities": PRIORITIES,
            "accents": ACCENTS,
            "today": date.today(),
        }

    @app.template_filter("short_date")
    def short_date(value):
        if not value:
            return "No due date"
        return date.fromisoformat(value[:10]).strftime("%b %d").replace(" 0", " ")

    @app.template_filter("event_date")
    def event_date(value):
        return datetime.fromisoformat(value).astimezone().strftime("%b %d, %I:%M %p")

    @app.get("/health")
    def health():
        return {"app": "workbench-starter", "status": "ok", "version": "1.1.0"}

    
    
    @app.get("/")
    def index():
        query = request.args.get("q", "").strip()[:120]
        status = request.args.get("status", "")
        if status not in STATUSES:
            status = ""
        view = "list" if request.args.get("view") == "list" else "board"

        items = db.list_items(g.workspace_id, query, status)
        groups = {
            key: [item for item in items if item["status"] == key]
            for key in STATUSES
        }

        return render_template(
            "index.html",
            page="board",
            items=items,
            groups=groups,
            query=query,
            selected_status=status,
            view=view,
            recent_events=db.events(g.workspace_id, 4),
            destinations=db.list_destinations(g.workspace_id),
        )

    @app.route("/items/new", methods=["GET", "POST"])
    def new_item():
        values = {"title": "", "description": "", "category": "General", "status": "todo", "priority": "medium", "due_date": ""}
        if request.args.get("status") in STATUSES:
            values["status"] = request.args["status"]
        errors = {}
        if request.method == "POST":
            values, errors = validate_item(request.form)
            if not errors:
                with db.transaction() as connection:
                    db.create_item(connection, g.workspace_id, values)
                    db.log_event(connection, g.workspace_id, "added", values["title"])
                flash("Item added. A good place to start.", "success")
                return redirect(url_for("index"), code=303)
        return render_template("item_form.html", page="board", values=values, errors=errors,
                               editing=False, item_id=None), 422 if errors else 200

    @app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
    def edit_item(item_id):
        item = owned_item(item_id, archived=False)
        values = item
        errors = {}
        if request.method == "POST":
            values, errors = validate_item(request.form)
            if not errors:
                with db.transaction() as connection:
                    db.update_item(connection, g.workspace_id, item_id, values)
                    db.log_event(connection, g.workspace_id, "edited", values["title"])
                flash("Changes saved.", "success")
                return redirect(url_for("index"), code=303)
        return render_template("item_form.html", page="board", values=values, errors=errors,
                               editing=True, item_id=item_id), 422 if errors else 200

    @app.post("/items/<int:item_id>/move")
    def move_item(item_id):
        status = request.form.get("status", "")
        if status not in STATUSES:
            abort(400, description="Choose a valid item status.")
        item = owned_item(item_id, archived=False)
        with db.transaction() as connection:
            db.move_item(connection, g.workspace_id, item_id, status)
            db.log_event(connection, g.workspace_id, "moved", item["title"] + " · " + STATUSES[status])
        flash("Moved to " + STATUSES[status] + ".", "success")
        return redirect(url_for("index"), code=303)

    @app.post("/items/<int:item_id>/remove")
    def remove_item(item_id):
        # Students can follow the call to history.push() into backend/stack.py.
        with db.transaction() as connection:
            item = owned_item(item_id, archived=False)
            history = HistoryBuffer(db.load_history(connection, g.workspace_id))
            history.push(item_id)
            db.archive_item(connection, g.workspace_id, item_id)
            db.save_history(connection, g.workspace_id, history.to_list())
            db.log_event(connection, g.workspace_id, "removed", item["title"])
        flash("Moved to the recovery tray. You can bring it back anytime.", "success")
        return redirect(url_for("index"), code=303)

    @app.get("/recovery")
    def recovery():
        history = HistoryBuffer(db.load_history(db.get_db(), g.workspace_id))
        next_item = None
        if not history.is_empty():
            next_item = db.get_item(g.workspace_id, history.peek(), archived=True)
        archived = {item["id"]: item for item in db.list_items(g.workspace_id, archived=True)}
        # Display chronology is separate from the class's next-to-restore rule.
        # The saved insertion order also avoids ties between removal timestamps.
        recently_removed = [archived[item_id] for item_id in reversed(history.to_list()) if item_id in archived]
        return render_template("recovery.html", page="recovery",
                               items=recently_removed,
                               next_item=next_item, history_size=history.size())

    @app.post("/recovery/restore")
    def restore_item():
        # The website uses the class's pop() result. SQL never chooses the next ID.
        restored = None
        with db.transaction() as connection:
            history = HistoryBuffer(db.load_history(connection, g.workspace_id))
            while not history.is_empty():
                next_id = history.pop()
                item = db.get_item(g.workspace_id, next_id, archived=True)
                if item:
                    db.restore_item(connection, g.workspace_id, next_id)
                    db.log_event(connection, g.workspace_id, "restored", item["title"])
                    restored = item
                    break
            db.save_history(connection, g.workspace_id, history.to_list())
        flash('Restored "' + restored["title"] + '".' if restored else "The recovery tray is empty.",
              "success" if restored else "info")
        return redirect(url_for("recovery"), code=303)

    @app.get("/activity")
    def activity():
        return render_template("activity.html", page="activity", events=db.events(g.workspace_id))

    @app.get("/guide")
    def guide():
        return render_template("guide.html", page="guide")

    @app.route("/settings", methods=["GET", "POST"])
    def settings():
        errors = {}
        values = db.get_workspace(g.workspace_id)
        if request.method == "POST":
            values = {"name": request.form.get("name", "").strip(), "accent": request.form.get("accent", "pine")}
            if not 1 <= len(values["name"]) <= 40:
                errors["name"] = "Use between 1 and 40 characters."
            if values["accent"] not in ACCENTS:
                errors["accent"] = "Choose one of the available colors."
            if not errors:
                with db.transaction() as connection:
                    db.update_workspace(connection, g.workspace_id, values["name"], values["accent"])
                    db.log_event(connection, g.workspace_id, "edited", "Workspace preferences")
                flash("Your workspace, your way. Preferences saved.", "success")
                return redirect(url_for("settings"), code=303)
        return render_template("settings.html", page="settings", values=values, errors=errors), 422 if errors else 200

    @app.get("/trips/new")
    def trip_form():
        return render_template("trip_form.html", page="travel")

    @app.get("/travel")
    def travel_dashboard():
        destinations = db.list_destinations(g.workspace_id)
        stats = db.travel_stats(g.workspace_id)
        trips = db.list_trips(g.workspace_id)
        return render_template(
            "travel.html",
            page="travel",
            destinations=destinations,
            stats=stats,
            trips=trips,
        )
    
    @app.post("/destinations/toggle")
    def toggle_travel_destination():
        country = request.form.get("country", "").strip()
        if not country or len(country) > 100:
            return jsonify({"error": "Invalid country name."}), 400

        existing = next(
            (
                item for item in db.list_destinations(g.workspace_id)
                if item["country"].casefold() == country.casefold()
            ),
            None,
        )

        if existing:
            db.delete_destination(g.workspace_id, existing["id"])
            return jsonify({"saved": False, "country": country})

        values = {
            "country": country,
            "region": request.form.get("region", "").strip()[:100],
            "capital": request.form.get("capital", "").strip()[:100],
            "currency": request.form.get("currency", "").strip()[:100],
            "language": request.form.get("language", "").strip()[:100],
            "flag": request.form.get("flag", "").strip()[:20],
            "status": "wishlist",
            "priority": "medium",
            "notes": "",
            "estimated_budget": 0,
            "actual_budget": 0,
        }

        db.save_destination(g.workspace_id, values)
        return jsonify({"saved": True, "country": country})


    @app.post("/destinations/save")
    def save_travel_destination():
        values = {
            "country": request.form.get("country", "").strip(),
            "region": request.form.get("region", "").strip(),
            "capital": request.form.get("capital", "").strip(),
            "currency": request.form.get("currency", "").strip(),
            "language": request.form.get("language", "").strip(),
            "flag": request.form.get("flag", "").strip(),
            "status": request.form.get("status", "wishlist").strip(),
            "priority": request.form.get("priority", "medium").strip(),
            "notes": request.form.get("notes", "").strip(),
            "estimated_budget": request.form.get("estimated_budget", "0").strip(),
            "actual_budget": request.form.get("actual_budget", "0").strip(),
        }

        errors = []
        if not 1 <= len(values["country"]) <= 100:
            errors.append("Enter a country name.")
        if values["status"] not in {"wishlist", "planning", "visited"}:
            errors.append("Choose a valid travel status.")
        if values["priority"] not in PRIORITIES:
            errors.append("Choose a valid priority.")
        if len(values["notes"]) > 2000:
            errors.append("Notes must be 2,000 characters or fewer.")

        for field in ("estimated_budget", "actual_budget"):
            try:
                amount = float(values[field] or 0)
                if not 0 <= amount < 1_000_000_000:
                    raise ValueError
                values[field] = amount
            except (TypeError, ValueError):
                errors.append("Budget amounts must be valid non-negative numbers.")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for("travel_dashboard"), code=303)

        db.save_destination(g.workspace_id, values)
        flash("Destination saved to your travel list.", "success")
        return redirect(url_for("travel_dashboard"), code=303)

    @app.post("/destinations/<int:destination_id>/delete")
    def remove_travel_destination(destination_id):
        destination = db.get_destination(g.workspace_id, destination_id)
        if destination is None:
            abort(404, description="That destination is not in your travel list.")

        db.delete_destination(g.workspace_id, destination_id)
        flash("Destination removed.", "success")
        return redirect(url_for("travel_dashboard"), code=303)

    @app.post("/trips/new")
    def new_trip():
        values = {
            "title": request.form.get("title", "").strip(),
            "notes": request.form.get("notes", "").strip(),
            "start_date": request.form.get("start_date", "").strip(),
            "end_date": request.form.get("end_date", "").strip(),
            "budget": request.form.get("budget", "0").strip(),
        }

        errors = []
        if not 1 <= len(values["title"]) <= 100:
            errors.append("Trip title must be between 1 and 100 characters.")
        if len(values["notes"]) > 2000:
            errors.append("Trip notes must be 2,000 characters or fewer.")

        for field in ("start_date", "end_date"):
            if values[field]:
                try:
                    date.fromisoformat(values[field])
                except ValueError:
                    errors.append("Enter valid trip dates.")
        if values["start_date"] and values["end_date"]:
            if values["end_date"] < values["start_date"]:
                errors.append("The trip end date cannot be before its start date.")

        try:
            values["budget"] = float(values["budget"] or 0)
            if not 0 <= values["budget"] < 1_000_000_000:
                raise ValueError
        except (TypeError, ValueError):
            errors.append("Enter a valid non-negative trip budget.")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for("travel_dashboard"), code=303)

        trip_id = db.create_trip(g.workspace_id, values)
        flash("Trip created! Add activities to build your itinerary.", "success")
        return redirect(url_for("trip_detail", trip_id=trip_id), code=303)

    @app.get("/trips/<int:trip_id>")
    def trip_detail(trip_id):
        trip = db.get_trip(g.workspace_id, trip_id)
        if trip is None:
            abort(404, description="That trip is not available in this workspace.")

        return render_template(
            "trip.html",
            page="travel",
            trip=trip,
            itinerary=db.list_itinerary(trip_id),
            destinations=db.list_destinations(g.workspace_id),
        )

    @app.post("/trips/<int:trip_id>/itinerary/add")
    def add_trip_activity(trip_id):
        trip = db.get_trip(g.workspace_id, trip_id)
        if trip is None:
            abort(404, description="That trip is not available in this workspace.")

        values = {
            "activity": request.form.get("activity", "").strip(),
            "activity_date": request.form.get("activity_date", "").strip(),
            "start_time": request.form.get("start_time", "").strip(),
            "end_time": request.form.get("end_time", "").strip(),
            "location": request.form.get("location", "").strip(),
            "notes": request.form.get("notes", "").strip(),
            "destination_id": request.form.get("destination_id", "").strip(),
            "estimated_cost": request.form.get("estimated_cost", "0").strip(),
            "actual_cost": request.form.get("actual_cost", "0").strip(),
        }

        errors = []
        if not 1 <= len(values["activity"]) <= 120:
            errors.append("Activity must be between 1 and 120 characters.")
        if len(values["location"]) > 200 or len(values["notes"]) > 1500:
            errors.append("Location or notes are too long.")

        if values["activity_date"]:
            try:
                date.fromisoformat(values["activity_date"])
            except ValueError:
                errors.append("Enter a valid activity date.")

        if values["start_time"] and values["end_time"]:
            if values["end_time"] < values["start_time"]:
                errors.append("Activity end time cannot be before its start time.")

        if values["destination_id"]:
            try:
                destination_id = int(values["destination_id"])
                if db.get_destination(g.workspace_id, destination_id) is None:
                    errors.append("Choose a destination from your travel list.")
                else:
                    values["destination_id"] = destination_id
            except ValueError:
                errors.append("Choose a valid destination.")

        for field in ("estimated_cost", "actual_cost"):
            try:
                amount = float(values[field] or 0)
                if not 0 <= amount < 1_000_000_000:
                    raise ValueError
                values[field] = amount
            except (TypeError, ValueError):
                errors.append("Activity costs must be valid non-negative numbers.")

        if errors:
            for error in errors:
                flash(error, "error")
            return redirect(url_for("trip_detail", trip_id=trip_id), code=303)

        db.add_itinerary_item(trip_id, values)
        flash("Activity added to your itinerary.", "success")
        return redirect(url_for("trip_detail", trip_id=trip_id), code=303)

    @app.post("/trips/<int:trip_id>/itinerary/<int:item_id>/delete")
    def remove_trip_activity(trip_id, item_id):
        trip = db.get_trip(g.workspace_id, trip_id)
        if trip is None:
            abort(404, description="That trip is not available in this workspace.")

        db.delete_itinerary_item(trip_id, item_id)
        flash("Activity removed from the itinerary.", "success")
        return redirect(url_for("trip_detail", trip_id=trip_id), code=303)

    @app.errorhandler(400)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def friendly_error(error):
        return render_template("error.html", page="", error=error), error.code

    return app


def owned_item(item_id, archived=None):
    item = db.get_item(g.workspace_id, item_id, archived)
    if item is None:
        abort(404, description="That item is not available in this workspace.")
    return item


def validate_item(form):
    values = {key: form.get(key, "").strip() for key in
              ("title", "description", "category", "status", "priority", "due_date")}
    errors = {}
    if not 1 <= len(values["title"]) <= 100:
        errors["title"] = "Give your item a title between 1 and 100 characters."
    if len(values["description"]) > 1500:
        errors["description"] = "Keep the description within 1,500 characters."
    if not 1 <= len(values["category"]) <= 30:
        errors["category"] = "Use a category between 1 and 30 characters."
    if values["status"] not in STATUSES:
        errors["status"] = "Choose a valid status."
    if values["priority"] not in PRIORITIES:
        errors["priority"] = "Choose a valid priority."
    if values["due_date"]:
        try:
            date.fromisoformat(values["due_date"])
        except ValueError:
            errors["due_date"] = "Choose a valid date."
    return values, errors


def local_secret(instance_path):
    """Create a local signing key once. Keep the same browser workspace on restart."""
    Path(instance_path).mkdir(parents=True, exist_ok=True)
    path = Path(instance_path) / ".secret_key"
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        value = secrets.token_hex(32)
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(value)
            try:
                path.chmod(0o600)
            except OSError:
                pass
            return value
        except FileExistsError:
            return path.read_text(encoding="utf-8").strip()


if __name__ == "__main__":
    from run import main
    raise SystemExit(main())
