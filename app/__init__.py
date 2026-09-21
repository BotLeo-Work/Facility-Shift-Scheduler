"""Application factory for Facility Shift Scheduler."""

import os

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
        """Render the selected Monday-Sunday schedule."""
        selected_start = request.args.get("start")
        try:
            week_start = date.fromisoformat(selected_start) if selected_start else date.today()
        except ValueError:
            abort(400, description="The schedule start date must use YYYY-MM-DD format.")
        week_start -= timedelta(days=week_start.weekday())
        week_end = week_start + timedelta(days=7)

        shifts_by_day = [[] for _ in range(7)]
        for row in db.list_shifts(
            week_start.isoformat(),
            week_end.isoformat(),
        ):
            start_at = datetime.fromisoformat(row["start_at"])
            end_at = datetime.fromisoformat(row["end_at"])
            day_index = (start_at.date() - week_start).days
            if 0 <= day_index < 7:
                schedule_start = start_at.replace(hour=8, minute=0, second=0)
                schedule_end = start_at.replace(hour=22, minute=0, second=0)
                total_minutes = (schedule_end - schedule_start).total_seconds() / 60
                start_minutes = max(0, (start_at - schedule_start).total_seconds() / 60)
                duration_minutes = max(30, (end_at - start_at).total_seconds() / 60)
                shifts_by_day[day_index].append(
                    {
                        "name": row["name"],
                        "initials": "".join(part[0] for part in row["name"].split()[:2]).upper(),
                        "time": f"{start_at:%I:%M}".lstrip("0") + " – " + f"{end_at:%I:%M}".lstrip("0"),
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
        today_shifts = shifts_by_day[(date.today() - week_start).days] if 0 <= (date.today() - week_start).days < 7 else []
        return render_template(
            "schedule.html",
            week_start=week_start,
            week_end=week_end - timedelta(days=1),
            week_label=f"{week_start:%B} {week_start.day}\u2013{(week_end - timedelta(days=1)).day}, {week_end.year}",
            days=days,
            today=date.today(),
            today_label=f"{date.today():%B} {date.today().day}",
            today_shifts=today_shifts,
            previous_week=week_start - timedelta(days=7),
            next_week=week_start + timedelta(days=7),
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
