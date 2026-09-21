"""Application factory for Facility Shift Scheduler."""

import os

from flask import Flask, render_template


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
        """Render the first-pass weekly schedule interface."""
        return render_template("schedule.html")

    return app
