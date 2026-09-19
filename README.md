# Facility Shift Scheduler

A simple web application that helps grocery-store managers create, edit, and
view employee shifts without relying on error-prone spreadsheets.

## Team goal

Build an intuitive schedule manager that reduces scheduling time and avoids
common conflicts, such as double-booking an employee or assigning a shift with
an invalid time range.

## Starter stack

- **Python + Flask** — small, approachable web application
- **SQLite** — local database; no separate server needed
- **HTML/CSS** — schedule and form screens
- **pytest** — lightweight automated checks

## How to start the project

From the project folder, create and activate a virtual environment, install
the dependencies, then start Flask:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --debug
```

Open the weekly schedule at [http://127.0.0.1:5000/schedule](http://127.0.0.1:5000/schedule).
Use `Ctrl+C` in the terminal to stop the server.

## Project map

| Path | Purpose | Suggested owner |
| --- | --- | --- |
| `app/__init__.py` | Flask app setup and routes | Integration / backend |
| `app/db.py` | SQLite schema and database helpers | Database |
| `app/templates/` | Pages for schedule viewing and editing | UI / frontend |
| `app/static/` | CSS and browser-side assets | UI / frontend |
| `tests/` | Automated behavior tests | QA / testing |
| `docs/ARCHITECTURE.md` | Shared design decisions and workflow | All teammates |

## Core features for the first version

1. Add, edit, and delete employee shifts.
2. Show a clear schedule by day or week.
3. Prevent obvious errors: missing employee, invalid start/end times, and
   overlapping shifts for the same employee.

## Working together

1. Pull the latest `main` before beginning work.
2. Create a focused branch, for example `feature/schedule-view`.
3. Make small, descriptive commits.
4. Push the branch and open a pull request for teammates to review.
5. Keep database changes documented in `docs/ARCHITECTURE.md`.

See [the architecture guide](docs/ARCHITECTURE.md) for component boundaries,
data model, and a suggested division of work.

### This is Connor's Edit

For the team's branching, pull-request, and conflict-avoidance process, see
[the GitHub workflow guide](docs/GITHUB_WORKFLOW.md).
