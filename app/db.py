"""SQLite connection, schema, and small query helpers."""

import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


SCHEMA = """
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees (id)
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        # SQLite ignores foreign keys unless asked, and we rely on the link
        # from a shift to its employee.
        g.db.execute("PRAGMA foreign_keys = ON")
        # A fresh SQLite file receives its tables as soon as the application
        # opens it, which keeps first-time setup and test databases simple.
        g.db.executescript(SCHEMA)
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    get_db().executescript(SCHEMA)


# --- Employee queries -------------------------------------------------------
def list_employees(include_inactive=False):
    query = "SELECT id, name, role, active FROM employees"
    parameters = ()
    if not include_inactive:
        query += " WHERE active = 1"
    query += " ORDER BY name"
    return get_db().execute(query, parameters).fetchall()


def create_employee(name, role):
    name = name.strip()
    role = role.strip()
    if not name or not role:
        raise ValueError("Employee name and role are required.")

    db = get_db()
    cursor = db.execute(
        "INSERT INTO employees (name, role) VALUES (?, ?)",
        (name, role),
    )
    db.commit()
    return get_employee(cursor.lastrowid)


def update_employee(employee_id, name, role, active=True):
    name = name.strip()
    role = role.strip()
    if not name or not role:
        raise ValueError("Employee name and role are required.")

    db = get_db()
    db.execute(
        "UPDATE employees SET name = ?, role = ?, active = ? WHERE id = ?",
        (name, role, int(bool(active)), employee_id),
    )
    db.commit()
    return get_employee(employee_id)


def deactivate_employee(employee_id):
    db = get_db()
    db.execute("UPDATE employees SET active = 0 WHERE id = ?", (employee_id,))
    db.commit()


def get_employee(employee_id):
    return get_db().execute(
        "SELECT id, name, role, active FROM employees WHERE id = ?", (employee_id,)
    ).fetchone()



# --- Shift queries -------------------------------------------------------
# Every shift is read through this one SELECT so that callers always get the
# same columns, including the employee's name for display.

SHIFT_SELECT = """
SELECT shifts.id,
       shifts.employee_id,
       shifts.start_at,
       shifts.end_at,
       shifts.notes,
       employees.name AS employee_name,
       employees.role AS employee_role
FROM shifts
LEFT JOIN employees ON employees.id = shifts.employee_id
"""


def get_shift(shift_id):
    return get_db().execute(SHIFT_SELECT + " WHERE shifts.id = ?", (shift_id,)).fetchone()


def list_shifts(start=None, end=None):
    """Return shifts overlapping the window, earliest first.

    A shift counts as inside the window when any part of it falls there, which
    is what a weekly calendar needs to draw. Either bound may be ``None``.
    """
    return get_db().execute(
        SHIFT_SELECT
        + """
        WHERE (:end IS NULL OR shifts.start_at < :end)
          AND (:start IS NULL OR shifts.end_at > :start)
        ORDER BY shifts.start_at, shifts.id
        """,
        {"start": start, "end": end},
    ).fetchall()


def shifts_for_employee(employee_id, exclude_id=None):
    """Return one employee's shifts, optionally skipping the one being edited."""
    return get_db().execute(
        SHIFT_SELECT
        + """
        WHERE shifts.employee_id = :employee_id
          AND (:exclude_id IS NULL OR shifts.id != :exclude_id)
        ORDER BY shifts.start_at, shifts.id
        """,
        {"employee_id": employee_id, "exclude_id": exclude_id},
    ).fetchall()


def insert_shift(employee_id, start_at, end_at, notes=None):
    """Store a new shift and return its id."""
    db = get_db()
    cursor = db.execute(
        "INSERT INTO shifts (employee_id, start_at, end_at, notes) VALUES (?, ?, ?, ?)",
        (employee_id, start_at, end_at, notes),
    )
    db.commit()
    return cursor.lastrowid


def update_shift(shift_id, employee_id, start_at, end_at, notes=None):
    """Overwrite a shift with already-validated values."""
    db = get_db()
    db.execute(
        """
        UPDATE shifts
           SET employee_id = ?, start_at = ?, end_at = ?, notes = ?
         WHERE id = ?
        """,
        (employee_id, start_at, end_at, notes, shift_id),
    )
    db.commit()


def delete_shift(shift_id):
    """Remove a shift. Returns True when a row was actually deleted."""
    db = get_db()
    cursor = db.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
    db.commit()
    return cursor.rowcount > 0


# --- Command line --------------------------------------------------------


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Create the database tables if they do not exist yet."""
    init_db()
    click.echo(f"Database ready at {current_app.config['DATABASE']}")


@click.command("seed-demo")
@with_appcontext
def seed_demo_command():
    """Add a few employees so the shift routes can be tried out.

    Temporary scaffolding: remove this once the employee management routes
    land and employees can be added through the app.
    """
    db = get_db()
    if db.execute("SELECT COUNT(*) AS total FROM employees").fetchone()["total"]:
        click.echo("Employees already exist; nothing to add.")
        return

    db.executemany(
        "INSERT INTO employees (name, role, active) VALUES (?, ?, ?)",
        [
            ("Alex Johnson", "Floor associate", 1),
            ("Tessa Reed", "Floor associate", 1),
            ("Maria Chen", "Store manager", 1),
            ("Sam Kim", "Cashier", 1),
            ("Leo Ortiz", "Stock associate", 0),
        ],
    )
    db.commit()
    for employee in db.execute("SELECT id, name, active FROM employees ORDER BY id"):
        status = "active" if employee["active"] else "inactive"
        click.echo(f"  {employee['id']}  {employee['name']} ({status})")


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(seed_demo_command)
