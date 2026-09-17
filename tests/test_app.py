from app import create_app


def test_home_page_reports_running():
    app = create_app({"TESTING": True, "DATABASE": ":memory:"})
    response = app.test_client().get("/")

    assert response.status_code == 200
    assert response.json["message"] == "Facility Shift Scheduler is running."
