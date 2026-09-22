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
    assert b"September 14\xe2\x80\x9320, 2026" in response.data
    assert b"Store floor coverage" in response.data