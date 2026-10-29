# FRONTEND — what the user sees

**Work here to change the pages, colors, layout, and interface.**

| File | Job |
| --- | --- |
| `templates/base.html` | Shared navigation, page wrapper, and stylesheet links |
| `templates/index.html` | Board/list view and search/filter controls |
| `templates/item_form.html` | Create/edit item form |
| `templates/recovery.html` | Recovery tray and restore button |
| `templates/activity.html` | Activity history |
| `templates/settings.html` | Workspace name and accent settings |
| `templates/guide.html` | Student instructions and repository map |
| `templates/error.html` | Friendly error screen |
| `templates/macros.html` | Reusable template pieces and icons |
| `static/style.css` | Visual styles and responsive layouts |
| `static/favicon.svg` | Browser tab icon |

These HTML files include Jinja template expressions. Flask fills in the data
before sending the page to the browser. Run the **root** `START_WEBSITE.bat` or
`python run.py`; do not double-click a template or run a separate frontend server.

Save HTML/CSS edits and refresh the browser. Use Ctrl+F5 if CSS is cached.
Keep `url_for(...)`, form field names, and the hidden `csrf_token` connected to
the corresponding routes in `../backend/app.py`. The browser's stylesheet URL
remains `/static/style.css`, even though the file lives in `frontend/static/`.

The Stack challenge is **not here**: edit `../backend/stack.py`.

[Back to the project](../README.md) · [Repository map](../docs/REPOSITORY_MAP.md)
