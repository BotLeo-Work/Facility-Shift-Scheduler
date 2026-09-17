"""Application factory for Facility Shift Scheduler."""

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE="instance/shift_scheduler.sqlite",
    )

    if test_config:
        app.config.update(test_config)

    from . import db
    db.init_app(app)

    @app.get("/")
    def index():
        return {"message": "Facility Shift Scheduler is running."}

    return app
