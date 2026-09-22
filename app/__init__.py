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
        return render_template("schedule.html")


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
