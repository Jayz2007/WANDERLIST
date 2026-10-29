# CHALLENGE — acceptance checks, not an answer

The file students edit is **`../backend/stack.py`**. This folder contains checks
that describe the target LIFO behavior; do not edit assertions to make them pass.

Run from the project root:

```powershell
.\CHECK_STACK.bat
```

Or `python challenge/check_stack.py` after installing the requirements.

The checker tests push/pop order, peek behavior, empty handling, storage order
and copying, and restoration through the real Flask website. It imports the
same `backend.stack.HistoryBuffer` used by the routes.

The starter deliberately remains FIFO, so some checks fail until the activity
is completed. Those failures do not mean the website is broken. Use
`RUN_TESTS.bat` for the separate website checks.
