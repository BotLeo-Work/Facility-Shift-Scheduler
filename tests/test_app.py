from app import create_app


def test_home_page_reports_running():
    app = create_app({"TESTING": True, "DATABASE": ":memory:"})
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert response.get_json()["message"] == "Facility Shift Scheduler is running."


def test_schedule_page_renders_weekly_planner():
    app = create_app({"TESTING": True, "DATABASE": ":memory:"})
    response = app.test_client().get("/schedule")

    assert response.status_code == 200
    assert b"Store floor coverage" in response.data


def test_employee_can_be_created_edited_and_deactivated(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    client = app.test_client()

    response = client.post(
        "/employees/new",
        data={"name": "Alex Johnson", "role": "Floor associate"},
    )
    assert response.status_code == 302

    response = client.get("/employees")
    assert b"Alex Johnson" in response.data
    assert b"Floor associate" in response.data

    response = client.post(
        "/employees/1/edit",
        data={"name": "Alex J.", "role": "Cashier", "active": "on"},
    )
    assert response.status_code == 302

    response = client.post("/employees/1/deactivate")
    assert response.status_code == 302
    response = client.get("/employees")
    assert b"Alex J." in response.data
    assert b"Inactive" in response.data


def test_employee_form_rejects_missing_required_fields(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    response = app.test_client().post(
        "/employees/new",
        data={"name": "", "role": "Cashier"},
    )

    assert response.status_code == 200
    assert b"Employee name and role are required." in response.data


def test_schedule_page_renders_query_results(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    client = app.test_client()
    client.post(
        "/employees/new",
        data={"name": "Jordan Lee", "role": "Cashier"},
    )

    with app.app_context():
        from app.db import get_db

        get_db().execute(
            "INSERT INTO shifts (employee_id, start_at, end_at) VALUES (?, ?, ?)",
            (1, "2026-09-21T09:00", "2026-09-21T17:00"),
        )
        get_db().commit()

    response = client.get("/schedule?start=2026-09-21")

    assert response.status_code == 200
    assert b"Jordan Lee" in response.data
    assert b"9:00 \xe2\x80\x93 5:00" in response.data
