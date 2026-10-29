"""Project paths. All paths start at the repository, not the terminal folder.

FRONTEND_DIR holds the browser-facing templates and CSS.
DATABASE_PATH is the SQLite data file, generated on first startup.
INSTANCE_DIR holds the private local session-signing key (not source code).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DATABASE_PATH = PROJECT_ROOT / "database" / "data" / "workbench.sqlite3"
INSTANCE_DIR = PROJECT_ROOT / "instance"
