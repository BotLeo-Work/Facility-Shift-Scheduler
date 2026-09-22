"""Manager-facing HTML routes."""

from datetime import date, datetime, timedelta

from flask import Blueprint, abort, redirect, render_template, request, url_for

from . import db, rules


bp = Blueprint("pages", __name__)


def _week_start(value=None):
    if value:
        try:
            selected = date.fromisoformat(value)
        except ValueError:
            abort(400, description="The schedule start date must use YYYY-MM-DD format.")
    else:
        selected = date.today()
    return selected - timedelta(days=selected.weekday())


def _format_time(value):
    return value.strftime("%I:%M").lstrip("0")


def _schedule_context(week_start):
    week_end = week_start + timedelta(days=7)
    shifts_by_day = [[] for _ in range(7)]

    for row in db.list_shifts(week_start.isoformat(), week_end.isoformat()):
        start_at = datetime.fromisoformat(row["start_at"])
        end_at = datetime.fromisoformat(row["end_at"])
        day_index = (start_at.date() - week_start).days
        if not 0 <= day_index < 7:
            continue

        schedule_start = start_at.replace(hour=8, minute=0, second=0)
        schedule_end = start_at.replace(hour=22, minute=0, second=0)
        total_minutes = (schedule_end - schedule_start).total_seconds() / 60
        start_minutes = max(0, (start_at - schedule_start).total_seconds() / 60)
        duration_minutes = max(30, (end_at - start_at).total_seconds() / 60)

        shifts_by_day[day_index].append(
            {
                "id": row["id"],
                "name": row["employee_name"],
                "initials": "".join(part[0] for part in row["employee_name"].split()[:2]).upper(),
                "time": f"{_format_time(start_at)} – {_format_time(end_at)}",
                "start_at": row["start_at"],
                "end_at": row["end_at"],
                "start": min(100, start_minutes / total_minutes * 100),
                "duration": min(100, duration_minutes / total_minutes * 100),
                "color": ("peach", "blue", "mint", "lavender", "yellow")[day_index % 5],
            }
        )

    days = [
        {
            "date": week_start + timedelta(days=index),
            "label": (week_start + timedelta(days=index)).strftime("%a").upper(),
            "shifts": shifts_by_day[index],
        }
        for index in range(7)
    ]
    today = date.today()
    today_index = (today - week_start).days
    today_shifts = shifts_by_day[today_index] if 0 <= today_index < 7 else []
    week_end_date = week_end - timedelta(days=1)
    return {
        "week_start": week_start,
        "week_label": f"{week_start:%B} {week_start.day}–{week_end_date.day}, {week_end.year}",
        "days": days,
        "today": today,
        "today_label": f"{today:%B} {today.day}",
        "today_shifts": today_shifts,
        "previous_week": week_start - timedelta(days=7),
        "next_week": week_start + timedelta(days=7),
    }


def _shift_form_context(shift=None, error=None, form=None):
    values = dict(form or {})
    if shift is not None and not form:
        values = {
            "employee_id": str(shift["employee_id"]),
            "start_at": shift["start_at"],
            "end_at": shift["end_at"],
            "notes": shift["notes"] or "",
        }
    return {
        "shift": shift,
        "employees": db.list_employees(),
        "values": values,
        "error": error,
    }


def _save_shift(form, shift=None):
    current = shift if shift is not None else None
    cleaned, errors = rules.clean_shift_fields(form, current=current)
    if errors or cleaned is None:
        return None, errors

    employee = db.get_employee(cleaned["employee_id"])
    employee_error = rules.check_employee(employee, cleaned["employee_id"])
    if employee_error:
        return None, [employee_error]

    exclude_id = shift["id"] if shift is not None else None
    conflicts = rules.find_conflicts(
        cleaned["start_at"],
        cleaned["end_at"],
        db.shifts_for_employee(cleaned["employee_id"], exclude_id=exclude_id),
    )
    if conflicts:
        return None, [rules.describe_conflict(conflict) for conflict in conflicts]

    if shift is None:
        shift_id = db.insert_shift(**cleaned)
    else:
        shift_id = shift["id"]
        db.update_shift(shift_id, **cleaned)
    return shift_id, []


@bp.get("/")
def index():
    return schedule()


@bp.get("/schedule")
def schedule():
    return render_template(
        "schedule.html",
        **_schedule_context(_week_start(request.args.get("start"))),
    )


@bp.get("/employees")
def employees():
    return render_template("employees.html", employees=db.list_employees(include_inactive=True))


@bp.route("/employees/new", methods=("GET", "POST"))
def new_employee():
    error = None
    if request.method == "POST":
        try:
            db.create_employee(request.form.get("name", ""), request.form.get("role", ""))
        except ValueError as exc:
            error = str(exc)
        else:
            return redirect(url_for("pages.employees"))
    return render_template("employee_form.html", employee=None, error=error)


@bp.route("/employees/<int:employee_id>/edit", methods=("GET", "POST"))
def edit_employee(employee_id):
    employee = db.get_employee(employee_id)
    if employee is None:
        abort(404)

    error = None
    if request.method == "POST":
        try:
            employee = db.update_employee(
                employee_id,
                request.form.get("name", ""),
                request.form.get("role", ""),
                request.form.get("active") == "on",
            )
        except ValueError as exc:
            error = str(exc)
        else:
            return redirect(url_for("pages.employees"))
    return render_template("employee_form.html", employee=employee, error=error)


@bp.post("/employees/<int:employee_id>/deactivate")
def deactivate_employee(employee_id):
    if db.get_employee(employee_id) is None:
        abort(404)
    db.deactivate_employee(employee_id)
    return redirect(url_for("pages.employees"))


@bp.get("/shifts")
def shifts():
    return render_template(
        "shifts.html",
        shifts=db.list_shifts(),
        open_only=False,
    )


@bp.get("/shifts/open")
def open_shifts():
    return render_template("shifts.html", shifts=[], open_only=True)


@bp.route("/shifts/new", methods=("GET", "POST"))
def new_shift():
    if request.method == "POST":
        shift_id, errors = _save_shift(request.form)
        if not errors:
            return redirect(url_for("pages.shifts"))
        return render_template(
            "shift_form.html",
            **_shift_form_context(error=" ".join(errors), form=request.form),
        )
    return render_template("shift_form.html", **_shift_form_context())


@bp.route("/shifts/<int:shift_id>/edit", methods=("GET", "POST"))
def edit_shift(shift_id):
    shift = db.get_shift(shift_id)
    if shift is None:
        abort(404)
    if request.method == "POST":
        saved_id, errors = _save_shift(request.form, shift=shift)
        if not errors:
            return redirect(url_for("pages.shifts"))
        return render_template(
            "shift_form.html",
            **_shift_form_context(shift=shift, error=" ".join(errors), form=request.form),
        )
    return render_template("shift_form.html", **_shift_form_context(shift=shift))


@bp.post("/shifts/<int:shift_id>/delete")
def delete_shift(shift_id):
    if not db.delete_shift(shift_id):
        abort(404)
    return redirect(url_for("pages.shifts"))