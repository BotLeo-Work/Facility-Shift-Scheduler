"""Tests for shift management: CRUD routes and the time checks behind them."""

import pytest

from app import create_app, db, rules


# --- Fixtures ------------------------------------------------------------
# A real file is used rather than ":memory:" because every request opens its
# own connection, and separate connections to ":memory:" get separate, empty
# databases.


@pytest.fixture
def app(tmp_path):
    application = create_app(
        {"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite")}
    )

    with application.app_context():
        db.init_db()
        handle = db.get_db()
        handle.executemany(
            "INSERT INTO employees (id, name, role, active) VALUES (?, ?, ?, ?)",
            [
                (1, "Alex Johnson", "Floor associate", 1),
                (2, "Tessa Reed", "Floor associate", 1),
                (3, "Leo Ortiz", "Stock associate", 0),
            ],
        )
        handle.commit()

    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def shift(client):
    """One stored shift: Alex Johnson, Thursday 9-5."""
    response = client.post(
        "/api/shifts",
        json={
            "employee_id": 1,
            "start_at": "2026-09-17T09:00",
            "end_at": "2026-09-17T17:00",
        },
    )
    assert response.status_code == 201
    return response.json["shift"]


# --- Rules (no database needed) ------------------------------------------


def test_end_must_be_after_start():
    _, errors = rules.clean_shift_fields(
        {"employee_id": 1, "start_at": "2026-09-17T17:00", "end_at": "2026-09-17T09:00"}
    )

    assert any("must be after" in error for error in errors)


def test_zero_length_shift_is_rejected():
    _, errors = rules.clean_shift_fields(
        {"employee_id": 1, "start_at": "2026-09-17T09:00", "end_at": "2026-09-17T09:00"}
    )

    assert any("must be after" in error for error in errors)


def test_times_are_normalised_to_minutes():
    cleaned, errors = rules.clean_shift_fields(
        {"employee_id": "1", "start_at": "2026-09-17T09:00:00", "end_at": "2026-09-17T17:00"}
    )

    assert errors == []
    assert cleaned["start_at"] == "2026-09-17T09:00"
    assert cleaned["employee_id"] == 1


def test_unparseable_time_explains_the_format():
    _, errors = rules.clean_shift_fields(
        {"employee_id": 1, "start_at": "next tuesday", "end_at": "2026-09-17T17:00"}
    )

    assert any("2026-09-17T09:00" in error for error in errors)


def test_missing_fields_are_all_reported_together():
    _, errors = rules.clean_shift_fields({})

    assert len(errors) == 3
    assert any("employee_id" in error for error in errors)
    assert any("start_at" in error for error in errors)
    assert any("end_at" in error for error in errors)


def test_overlapping_shift_is_found():
    existing = [{"start_at": "2026-09-17T09:00", "end_at": "2026-09-17T17:00"}]

    assert rules.find_conflicts("2026-09-17T16:00", "2026-09-17T20:00", existing)


def test_back_to_back_shifts_do_not_overlap():
    existing = [{"start_at": "2026-09-17T09:00", "end_at": "2026-09-17T17:00"}]

    assert rules.find_conflicts("2026-09-17T17:00", "2026-09-17T21:00", existing) == []


def test_shift_fully_inside_another_is_a_conflict():
    existing = [{"start_at": "2026-09-17T09:00", "end_at": "2026-09-17T17:00"}]

    assert rules.find_conflicts("2026-09-17T11:00", "2026-09-17T12:00", existing)


def test_a_bare_end_date_covers_the_whole_day():
    value, error = rules.parse_range_bound("2026-09-20", "end", end_of_day=True)

    assert error is None
    assert value == "2026-09-20T23:59"


# --- Creating shifts -----------------------------------------------------


def test_create_shift_stores_it(client, shift):
    assert shift["employee_name"] == "Alex Johnson"
    assert shift["start_at"] == "2026-09-17T09:00"

    listed = client.get("/api/shifts").json["shifts"]
    assert len(listed) == 1
    assert listed[0]["id"] == shift["id"]


def test_create_rejects_overlap_for_same_employee(client, shift):
    response = client.post(
        "/api/shifts",
        json={
            "employee_id": 1,
            "start_at": "2026-09-17T16:00",
            "end_at": "2026-09-17T20:00",
        },
    )

    assert response.status_code == 409
    assert "already has a shift" in response.json["errors"][0]


def test_two_employees_may_work_the_same_hours(client, shift):
    response = client.post(
        "/api/shifts",
        json={
            "employee_id": 2,
            "start_at": "2026-09-17T09:00",
            "end_at": "2026-09-17T17:00",
        },
    )

    assert response.status_code == 201


def test_create_rejects_unknown_employee(client):
    response = client.post(
        "/api/shifts",
        json={
            "employee_id": 99,
            "start_at": "2026-09-17T09:00",
            "end_at": "2026-09-17T17:00",
        },
    )

    assert response.status_code == 400
    assert "No employee with id 99" in response.json["errors"][0]


def test_create_rejects_inactive_employee(client):
    response = client.post(
        "/api/shifts",
        json={
            "employee_id": 3,
            "start_at": "2026-09-17T09:00",
            "end_at": "2026-09-17T17:00",
        },
    )

    assert response.status_code == 400
    assert "not an active employee" in response.json["errors"][0]


def test_create_rejects_backwards_times(client):
    response = client.post(
        "/api/shifts",
        json={
            "employee_id": 1,
            "start_at": "2026-09-17T17:00",
            "end_at": "2026-09-17T09:00",
        },
    )

    assert response.status_code == 400


def test_create_rejects_a_misspelled_field(client):
    response = client.post(
        "/api/shifts",
        json={
            "employeeId": 1,
            "start_at": "2026-09-17T09:00",
            "end_at": "2026-09-17T17:00",
        },
    )

    assert response.status_code == 400
    assert "employeeId" in response.json["errors"][0]


def test_create_accepts_a_posted_form(client):
    response = client.post(
        "/api/shifts",
        data={
            "employee_id": "2",
            "start_at": "2026-09-18T09:00",
            "end_at": "2026-09-18T17:00",
        },
    )

    assert response.status_code == 201


# --- Listing shifts ------------------------------------------------------


def test_list_filters_to_the_requested_week(client):
    client.post("/api/shifts", json={
        "employee_id": 1, "start_at": "2026-09-17T09:00", "end_at": "2026-09-17T17:00"})
    client.post("/api/shifts", json={
        "employee_id": 1, "start_at": "2026-09-28T09:00", "end_at": "2026-09-28T17:00"})

    listed = client.get("/api/shifts?start=2026-09-14&end=2026-09-20").json["shifts"]

    assert len(listed) == 1
    assert listed[0]["start_at"] == "2026-09-17T09:00"


def test_list_includes_a_shift_that_straddles_the_window(client):
    client.post("/api/shifts", json={
        "employee_id": 1, "start_at": "2026-09-13T22:00", "end_at": "2026-09-14T06:00"})

    listed = client.get("/api/shifts?start=2026-09-14&end=2026-09-20").json["shifts"]

    assert len(listed) == 1


def test_list_rejects_an_unreadable_date(client):
    response = client.get("/api/shifts?start=last-week")

    assert response.status_code == 400


# --- Editing and deleting ------------------------------------------------


def test_edit_changes_only_what_was_sent(client, shift):
    response = client.patch(
        "/api/shifts/{}".format(shift["id"]), json={"end_at": "2026-09-17T18:30"}
    )

    assert response.status_code == 200
    assert response.json["shift"]["end_at"] == "2026-09-17T18:30"
    assert response.json["shift"]["start_at"] == "2026-09-17T09:00"


def test_edit_does_not_clash_with_itself(client, shift):
    response = client.patch(
        "/api/shifts/{}".format(shift["id"]), json={"notes": "Covering the deli"}
    )

    assert response.status_code == 200
    assert response.json["shift"]["notes"] == "Covering the deli"


def test_edit_rejects_a_clash_with_another_shift(client, shift):
    client.post("/api/shifts", json={
        "employee_id": 1, "start_at": "2026-09-17T18:00", "end_at": "2026-09-17T22:00"})

    response = client.patch(
        "/api/shifts/{}".format(shift["id"]), json={"end_at": "2026-09-17T20:00"}
    )

    assert response.status_code == 409


def test_edit_rejects_backwards_times(client, shift):
    response = client.patch(
        "/api/shifts/{}".format(shift["id"]), json={"end_at": "2026-09-17T08:00"}
    )

    assert response.status_code == 400


def test_edit_missing_shift_returns_404(client):
    response = client.patch("/api/shifts/404", json={"end_at": "2026-09-17T18:00"})

    assert response.status_code == 404


def test_delete_removes_the_shift(client, shift):
    response = client.delete("/api/shifts/{}".format(shift["id"]))

    assert response.status_code == 200
    assert client.get("/api/shifts").json["shifts"] == []


def test_delete_missing_shift_returns_404(client):
    response = client.delete("/api/shifts/404")

    assert response.status_code == 404


def test_get_one_shift(client, shift):
    response = client.get("/api/shifts/{}".format(shift["id"]))

    assert response.status_code == 200
    assert response.json["shift"]["employee_name"] == "Alex Johnson"


# --- API mistakes still answer in JSON -----------------------------------


def test_bad_shift_id_returns_json_not_html(client):
    response = client.get("/api/shifts/abc")

    assert response.status_code == 404
    assert response.is_json
    assert "errors" in response.json


def test_wrong_method_returns_json_not_html(client):
    response = client.put("/api/shifts/1")

    assert response.status_code == 405
    assert response.is_json
    assert "PUT" in response.json["errors"][0]


def test_ordinary_pages_still_get_html_errors(client):
    response = client.get("/no-such-page")

    assert response.status_code == 404
    assert not response.is_json
