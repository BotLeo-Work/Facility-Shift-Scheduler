"""Application factory for Facility Shift Scheduler."""

import os
from datetime import date, datetime, time, timedelta

from flask import Flask, abort, redirect, render_template, request, url_for


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        # Keep the database inside the instance folder, addressed absolutely so
        # it does not move around with the directory Flask is started from.
        DATABASE=os.path.join(app.instance_path, "shift_scheduler.sqlite"),
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from . import db
    db.init_app(app)

    from . import shifts
    app.register_blueprint(shifts.bp)

    @app.get("/")
    def index():
        return {"message": "Facility Shift Scheduler is running."}

    @app.get("/schedule")
    def schedule():
        """Render a Monday-Sunday schedule using the shifts in SQLite."""
        requested_start = request.args.get("start")
        if requested_start:
            try:
                selected_day = date.fromisoformat(requested_start)
            except ValueError:
                abort(400, description="start must be a date such as 2026-09-21")
        else:
            selected_day = date.today()

        week_start = selected_day - timedelta(days=selected_day.weekday())
        week_end = week_start + timedelta(days=7)
        window_start = datetime.combine(week_start, time.min).strftime("%Y-%m-%dT%H:%M")
        window_end = datetime.combine(week_end, time.min).strftime("%Y-%m-%dT%H:%M")
        shifts = db.list_shifts(window_start, window_end)

        days = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            day_start = datetime.combine(day, time(hour=8))
            day_end = datetime.combine(day, time(hour=20))
            displayed = []

            for shift in shifts:
                shift_start = datetime.fromisoformat(shift["start_at"])
                shift_end = datetime.fromisoformat(shift["end_at"])
                if shift_start >= day_end or shift_end <= day_start:
                    continue

                visible_start = max(shift_start, day_start)
                visible_end = min(shift_end, day_end)
                displayed.append(
                    {
                        "id": shift["id"],
                        "employee_id": shift["employee_id"],
                        "employee_name": shift["employee_name"],
                        "employee_role": shift["employee_role"],
                        "start_at": shift["start_at"],
                        "end_at": shift["end_at"],
                        "notes": shift["notes"] or "",
                        "start_percent": (visible_start - day_start).total_seconds() / 43200 * 100,
                        "duration_percent": (visible_end - visible_start).total_seconds() / 43200 * 100,
                        "time_label": f"{shift_start.strftime('%I:%M')} – {shift_end.strftime('%I:%M')}",
                    }
                )

            days.append({"date": day, "shifts": displayed})

        return render_template(
            "schedule.html",
            employees=db.list_employees(),
            week_days=days,
            week_label=f"{week_start.strftime('%B')} {week_start.day}–{(week_end - timedelta(days=1)).day}, {week_end.year}",
            previous_week=(week_start - timedelta(days=7)).isoformat(),
            next_week=week_end.isoformat(),
            this_week=(date.today() - timedelta(days=date.today().weekday())).isoformat(),
        )


    @app.get("/employees")
    def employees():
        return render_template("employees.html", employees=db.list_employees(include_inactive=True))

    @app.route("/employees/new", methods=("GET", "POST"))
    def new_employee():
        error = None
        if request.method == "POST":
            try:
                db.create_employee(
                    request.form.get("name", ""),
                    request.form.get("role", ""),
                )
            except ValueError as exc:
                error = str(exc)
            else:
                return redirect(url_for("employees"))
        return render_template("employee_form.html", employee=None, error=error)

    @app.route("/employees/<int:employee_id>/edit", methods=("GET", "POST"))
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
                return redirect(url_for("employees"))
        return render_template("employee_form.html", employee=employee, error=error)

    @app.post("/employees/<int:employee_id>/deactivate")
    def deactivate_employee(employee_id):
        if db.get_employee(employee_id) is None:
            abort(404)
        db.deactivate_employee(employee_id)
        return redirect(url_for("employees"))

    return app
