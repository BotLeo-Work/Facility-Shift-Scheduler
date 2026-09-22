"""Application factory for Facility Shift Scheduler."""

import os

from flask import Flask


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

    @app.before_request
    def ensure_database():
        db.init_db()

    from . import shifts
    app.register_blueprint(shifts.bp)
    from . import routes
    app.register_blueprint(routes.bp)

    return app
