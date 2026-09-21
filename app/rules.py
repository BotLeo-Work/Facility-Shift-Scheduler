"""Scheduling rules for shifts.

Pure validation: no Flask, no SQL, no HTML.  A route gathers the data, these
helpers decide whether the change is allowed, and the route turns the returned
messages into a response the manager can read.

Times are handled as ISO strings normalised to whole minutes
("2026-09-17T09:00").  Because every stored time uses that one fixed width,
comparing them as plain text gives the same answer as comparing datetimes,
which is what lets SQLite sort and range-filter shifts without extra work.
"""

from datetime import datetime


TIME_FORMAT = "%Y-%m-%dT%H:%M"
EXAMPLE_TIME = "2026-09-17T09:00"
ALLOWED_FIELDS = ("employee_id", "start_at", "end_at", "notes")
NOTES_MAX_LENGTH = 500


def normalise_time(value, field):
    """Return ``(iso_string, error)`` for one start/end time."""
    if not isinstance(value, str) or not value.strip():
        return None, f"{field} is required and must be a date and time such as {EXAMPLE_TIME}."

    try:
        moment = datetime.fromisoformat(value.strip())
    except ValueError:
        return None, f"{field} must be a date and time such as {EXAMPLE_TIME}."

    if moment.tzinfo is not None:
        return None, f"{field} must not include a timezone offset; use the store's local time."

    return moment.strftime(TIME_FORMAT), None


def _clean_employee_id(value):
    # bool is a subclass of int, so True would otherwise sneak through as id 1.
    if value is None or isinstance(value, bool):
        return None, "employee_id must be the id number of an employee."

    try:
        employee_id = int(value)
    except (TypeError, ValueError):
        return None, "employee_id must be the id number of an employee."

    if employee_id <= 0:
        return None, "employee_id must be a positive id number."

    return employee_id, None


def _clean_notes(value):
    if value is None:
        return None, None

    if not isinstance(value, str):
        return None, "notes must be text."

    notes = value.strip()
    if not notes:
        return None, None

    if len(notes) > NOTES_MAX_LENGTH:
        return None, f"notes must be {NOTES_MAX_LENGTH} characters or fewer."

    return notes, None


def clean_shift_fields(payload, current=None):
    """Validate and normalise the fields of a shift.

    ``payload`` is the submitted body.  ``current`` is the shift as it is
    stored today when editing, so an edit only has to send the fields it wants
    to change.  Returns ``(cleaned, errors)``; ``cleaned`` is only complete and
    safe to store when ``errors`` is empty.
    """
    if not isinstance(payload, dict):
        return None, ["The shift must be sent as a JSON object."]

    errors = []

    unknown = sorted(set(payload) - set(ALLOWED_FIELDS))
    if unknown:
        errors.append(
            "Unknown field(s): " + ", ".join(unknown) + ". "
            "A shift accepts " + ", ".join(ALLOWED_FIELDS) + "."
        )

    current = dict(current) if current else {}
    cleaned = {}

    if "employee_id" in payload:
        employee_id, error = _clean_employee_id(payload["employee_id"])
        if error:
            errors.append(error)
        else:
            cleaned["employee_id"] = employee_id
    elif "employee_id" in current:
        cleaned["employee_id"] = current["employee_id"]
    else:
        errors.append("employee_id is required: a shift must belong to an employee.")

    for field in ("start_at", "end_at"):
        if field in payload:
            moment, error = normalise_time(payload[field], field)
            if error:
                errors.append(error)
            else:
                cleaned[field] = moment
        elif field in current:
            cleaned[field] = current[field]
        else:
            errors.append(f"{field} is required and must be a date and time such as {EXAMPLE_TIME}.")

    if "notes" in payload:
        notes, error = _clean_notes(payload["notes"])
        if error:
            errors.append(error)
        else:
            cleaned["notes"] = notes
    else:
        cleaned["notes"] = current.get("notes")

    # Only worth checking once both ends parsed cleanly.
    if "start_at" in cleaned and "end_at" in cleaned and cleaned["end_at"] <= cleaned["start_at"]:
        errors.append(
            f"end_at ({cleaned['end_at']}) must be after start_at ({cleaned['start_at']})."
        )

    if errors:
        return None, errors

    return cleaned, []


def check_employee(employee, employee_id):
    """Return an error message when a shift cannot be given to this employee."""
    if employee is None:
        return f"No employee with id {employee_id} exists."

    if not employee["active"]:
        return f"{employee['name']} is not an active employee and cannot be scheduled."

    return None


def find_conflicts(start_at, end_at, existing_shifts):
    """Return the shifts in ``existing_shifts`` that overlap ``start_at``-``end_at``.

    Two shifts overlap when each one starts before the other ends.  Shifts that
    merely touch -- one ending exactly when the next begins -- are allowed, so a
    manager can run back-to-back shifts without the app complaining.

    ``existing_shifts`` should already be narrowed to the same employee; this
    function does not care who works them.
    """
    return [
        shift
        for shift in existing_shifts
        if start_at < shift["end_at"] and shift["start_at"] < end_at
    ]


def describe_conflict(shift):
    """Turn an overlapping shift into a message a manager can act on."""
    who = shift["employee_name"] or f"Employee {shift['employee_id']}"
    return (
        f"{who} already has a shift from {shift['start_at']} to {shift['end_at']}. "
        "One employee cannot work two shifts at the same time."
    )


def parse_range_bound(value, field, end_of_day=False):
    """Return ``(iso_string, error)`` for a ``?start=``/``?end=`` filter value.

    Accepts a plain date ("2026-09-14") or a date and time.  A bare date given
    as ``end`` covers that whole day, so ``?start=2026-09-14&end=2026-09-20``
    reads as the full week a manager would expect.
    """
    text = (value or "").strip()
    if not text:
        return None, None

    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None, f"{field} must be a date (2026-09-14) or a date and time ({EXAMPLE_TIME})."

    if moment.tzinfo is not None:
        return None, f"{field} must not include a timezone offset; use the store's local time."

    if end_of_day and len(text) == 10:
        moment = moment.replace(hour=23, minute=59)

    return moment.strftime(TIME_FORMAT), None
