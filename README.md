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
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask --app app init-db            # once, to create the database tables
flask --app app seed-demo          # optional: a few employees to try shifts with
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

## Shift management API

Shifts are added, changed, and removed through these JSON endpoints. Every
write is checked first: the employee must exist and be active, `end_at` must be
after `start_at`, and the shift must not overlap another shift that employee
already works. Back-to-back shifts are allowed.

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/shifts?start=...&end=...` | List shifts overlapping a date range |
| `GET` | `/api/shifts/<id>` | Fetch one shift |
| `POST` | `/api/shifts` | Add a shift |
| `PATCH` | `/api/shifts/<id>` | Change part of a shift |
| `DELETE` | `/api/shifts/<id>` | Remove a shift |

Times use ISO format without a timezone, for example `2026-09-17T09:00`. The
range filter accepts a plain date too, and `end=2026-09-20` covers that whole
day.

```bash
curl -X POST http://127.0.0.1:5000/api/shifts -H "Content-Type: application/json" -d '{"employee_id": 1, "start_at": "2026-09-17T09:00", "end_at": "2026-09-17T17:00"}'
```

On Windows PowerShell, write `curl.exe` rather than `curl`, because plain
`curl` there is an alias for a different command that does not take these
options.

A rejected change comes back as `{"errors": ["..."]}` with a message written for
the manager to read: `400` for bad or missing fields, `409` for a clash with an
existing shift, `404` for a shift that does not exist.

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
