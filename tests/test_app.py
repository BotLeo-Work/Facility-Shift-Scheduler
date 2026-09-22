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