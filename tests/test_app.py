from app import create_app


def test_home_page_reports_running():
    app = create_app({"TESTING": True, "DATABASE": ":memory:"})
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert b"Store floor coverage" in response.data


def test_schedule_page_renders_weekly_planner():
    app = create_app({"TESTING": True, "DATABASE": ":memory:"})
    response = app.test_client().get("/schedule")

    assert response.status_code == 200
    assert b"Store floor coverage" in response.data


def test_shift_html_crud_uses_shared_validation(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    client = app.test_client()
    client.post("/employees/new", data={"name": "Jordan Lee", "role": "Cashier"})

    response = client.post(
        "/shifts/new",
        data={
            "employee_id": "1",
            "start_at": "2026-09-21T09:00",
            "end_at": "2026-09-21T17:00",
            "notes": "Opening shift",
        },
    )
    assert response.status_code == 302

    response = client.get("/shifts")
    assert b"Jordan Lee" in response.data
    assert b"Opening shift" not in response.data

    response = client.post(
        "/shifts/1/edit",
        data={
            "employee_id": "1",
            "start_at": "2026-09-21T10:00",
            "end_at": "2026-09-21T18:00",
            "notes": "Updated shift",
        },
    )
    assert response.status_code == 302

    response = client.post("/shifts/1/delete")
    assert response.status_code == 302
    assert b"No shifts have been scheduled yet." in client.get("/shifts").data


def test_shift_creation_allows_unassigned_employee_and_lists_open_shifts(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    client = app.test_client()

    response = client.post(
        "/shifts/new",
        data={
            "name": "Opening shift",
            "start_at": "2026-09-21T09:00",
            "end_at": "2026-09-21T17:00",
            "notes": "Needs coverage",
        },
    )
    assert response.status_code == 302

    open_page = client.get("/shifts/open")
    assert b"Opening shift" in open_page.data
    assert b"Add employee" in open_page.data
    assert b"/shifts/1/assign" in open_page.data

    schedule_page = client.get("/schedule")
    assert b"Opening shift" in schedule_page.data
    assert b"/shifts/1/assign" in schedule_page.data


def test_open_shift_assignment_form_lists_active_employees(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    client = app.test_client()
    client.post("/employees/new", data={"name": "Active Worker", "role": "Cashier"})
    client.post("/employees/new", data={"name": "Inactive Worker", "role": "Cashier"})
    client.post("/employees/2/deactivate")
    client.post(
        "/shifts/new",
        data={
            "name": "Opening shift",
            "start_at": "2026-09-21T09:00",
            "end_at": "2026-09-21T17:00",
        },
    )

    response = client.get("/shifts/1/assign")

    assert response.status_code == 200
    assert b'<select id="employee_ids" name="employee_ids"' in response.data
    assert b"Active Worker" in response.data
    assert b"Inactive Worker" not in response.data


def test_open_shift_can_be_assigned_from_employee_form(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")})
    client = app.test_client()
    client.post("/employees/new", data={"name": "Jordan Lee", "role": "Cashier"})
    client.post(
        "/shifts/new",
        data={
            "name": "Opening shift",
            "start_at": "2026-09-21T09:00",
            "end_at": "2026-09-21T17:00",
        },
    )

    response = client.post("/shifts/1/assign", data={"employee_id": "1"})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/shifts")
    assert b"Cashier" in client.get("/shifts").data