"""JSON routes for shift management: add, edit, delete, and view shifts.

These handlers stay deliberately thin.  They read the request, hand the work to
``rules`` for the time checks and to ``db`` for the SQL, then shape the answer.
Any rule about what makes a shift valid belongs in ``rules.py``, not here.

Status codes:
    400  the submitted fields are wrong or missing
    404  no shift with that id
    409  the shift clashes with one the employee already works
"""

from flask import Blueprint, jsonify, request

from . import db, rules


bp = Blueprint("shifts", __name__, url_prefix="/api/shifts")


def _payload():
    """Read the request body, accepting JSON or a posted HTML form."""
    data = request.get_json(silent=True)
    if data is not None:
        return data
    if request.form:
        return request.form.to_dict()
    return None


def _as_json(shift):
    return {
        "id": shift["id"],
        "employee_id": shift["employee_id"],
        "employee_name": shift["employee_name"],
        "employee_role": shift["employee_role"],
        "start_at": shift["start_at"],
        "end_at": shift["end_at"],
        "notes": shift["notes"],
    }


def _failed(messages, status=400):
    return jsonify({"errors": messages}), status


def _check_against_schedule(cleaned, exclude_id=None):
    """Run the rules that need the database. Returns ``(errors, status)``."""
    employee = db.get_employee(cleaned["employee_id"])
    employee_error = rules.check_employee(employee, cleaned["employee_id"])
    if employee_error:
        return [employee_error], 400

    conflicts = rules.find_conflicts(
        cleaned["start_at"],
        cleaned["end_at"],
        db.shifts_for_employee(cleaned["employee_id"], exclude_id=exclude_id),
    )
    if conflicts:
        return [rules.describe_conflict(shift) for shift in conflicts], 409

    return [], None


@bp.get("")
def list_shifts():
    """List shifts, optionally limited to a date range."""
    errors = []

    start, error = rules.parse_range_bound(request.args.get("start"), "start")
    if error:
        errors.append(error)

    end, error = rules.parse_range_bound(request.args.get("end"), "end", end_of_day=True)
    if error:
        errors.append(error)

    if errors:
        return _failed(errors)

    if start and end and end <= start:
        return _failed(["end must be after start."])

    shifts = db.list_shifts(start, end)
    return jsonify({"shifts": [_as_json(shift) for shift in shifts]})


@bp.get("/<int:shift_id>")
def get_shift(shift_id):
    """Fetch one shift, for an edit form to fill itself in."""
    shift = db.get_shift(shift_id)
    if shift is None:
        return _failed([f"No shift with id {shift_id} exists."], 404)

    return jsonify({"shift": _as_json(shift)})


@bp.post("")
def create_shift():
    """Add a shift once it passes every rule."""
    payload = _payload()
    if payload is None:
        return _failed(["Send the shift as JSON, for example {\"employee_id\": 1, "
                        "\"start_at\": \"2026-09-17T09:00\", \"end_at\": \"2026-09-17T17:00\"}."])

    cleaned, errors = rules.clean_shift_fields(payload)
    if errors:
        return _failed(errors)

    errors, status = _check_against_schedule(cleaned)
    if errors:
        return _failed(errors, status)

    shift_id = db.insert_shift(
        cleaned["employee_id"], cleaned["start_at"], cleaned["end_at"], cleaned["notes"]
    )
    return jsonify({"shift": _as_json(db.get_shift(shift_id))}), 201


@bp.patch("/<int:shift_id>")
def edit_shift(shift_id):
    """Change part of a shift, re-checking the rules against the new times."""
    existing = db.get_shift(shift_id)
    if existing is None:
        return _failed([f"No shift with id {shift_id} exists."], 404)

    payload = _payload()
    if payload is None:
        return _failed(["Send the fields to change as JSON, for example "
                        "{\"end_at\": \"2026-09-17T18:00\"}."])

    cleaned, errors = rules.clean_shift_fields(payload, current=existing)
    if errors:
        return _failed(errors)

    # The shift being edited must not count as a clash with itself.
    errors, status = _check_against_schedule(cleaned, exclude_id=shift_id)
    if errors:
        return _failed(errors, status)

    db.update_shift(
        shift_id,
        cleaned["employee_id"],
        cleaned["start_at"],
        cleaned["end_at"],
        cleaned["notes"],
    )
    return jsonify({"shift": _as_json(db.get_shift(shift_id))})


@bp.delete("/<int:shift_id>")
def remove_shift(shift_id):
    """Take a shift off the schedule."""
    if not db.delete_shift(shift_id):
        return _failed([f"No shift with id {shift_id} exists."], 404)

    return jsonify({"deleted": shift_id})


def _json_errors_under_api(state):
    """Answer API mistakes with JSON instead of Flask's HTML error pages.

    A page that asks for a shift expects JSON back even when it gets the
    address or the method wrong, otherwise reading the reply fails.  Flask
    raises these two during routing, before it knows which blueprint was
    meant, so they have to be registered on the application.  Anything
    outside /api/ is handed back untouched and still gets the normal pages.
    """
    app = state.app

    @app.errorhandler(404)
    def _not_found(error):
        if request.path.startswith("/api/"):
            return _failed(["There is nothing at " + request.path + "."], 404)
        return error

    @app.errorhandler(405)
    def _method_not_allowed(error):
        if request.path.startswith("/api/"):
            allowed = ", ".join(sorted(error.valid_methods or []))
            return _failed(
                [f"{request.method} is not allowed here. Try: {allowed}."], 405
            )
        return error


bp.record_once(_json_errors_under_api)
