"""SQLite connection and schema helpers."""

import sqlite3

from flask import current_app, g


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
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


def list_employees(include_inactive=False):
    query = "SELECT id, name, role, active FROM employees"
    parameters = ()
    if not include_inactive:
        query += " WHERE active = 1"
    query += " ORDER BY name"
    return get_db().execute(query, parameters).fetchall()


def get_employee(employee_id):
    return get_db().execute(
        "SELECT id, name, role, active FROM employees WHERE id = ?",
        (employee_id,),
    ).fetchone()


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


def list_shifts(start_at, end_at):
    return get_db().execute(
        """
        SELECT shifts.id, shifts.employee_id, shifts.start_at, shifts.end_at,
               shifts.notes, employees.name, employees.role
        FROM shifts
        JOIN employees ON employees.id = shifts.employee_id
        WHERE employees.active = 1
          AND shifts.start_at < ?
          AND shifts.end_at > ?
        ORDER BY shifts.start_at, employees.name
        """,
        (end_at, start_at),
    ).fetchall()


def init_app(app):
    app.teardown_appcontext(close_db)
