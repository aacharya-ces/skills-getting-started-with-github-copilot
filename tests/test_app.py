import copy
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities

# Store a deep copy of the original activities to reset state between tests
_original_activities = copy.deepcopy(activities)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset the in-memory activities dict before each test."""
    activities.clear()
    activities.update(copy.deepcopy(_original_activities))


client = TestClient(app)


# --- GET / ---

def test_root_redirects_to_index():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


# --- GET /activities ---

def test_get_activities_returns_all():
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 9


def test_get_activities_contain_expected_fields():
    response = client.get("/activities")
    data = response.json()
    for name, details in data.items():
        assert "description" in details
        assert "schedule" in details
        assert "max_participants" in details
        assert "participants" in details
        assert isinstance(details["participants"], list)


def test_get_activities_includes_known_activity():
    response = client.get("/activities")
    data = response.json()
    assert "Chess Club" in data
    assert data["Chess Club"]["schedule"] == "Fridays, 3:30 PM - 5:00 PM"


# --- POST /activities/{name}/signup ---

def test_signup_success():
    response = client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
    assert response.status_code == 200
    assert "newstudent@mergington.edu" in response.json()["message"]

    # Verify participant was added
    activities_resp = client.get("/activities")
    assert "newstudent@mergington.edu" in activities_resp.json()["Chess Club"]["participants"]


def test_signup_activity_not_found():
    response = client.post("/activities/Nonexistent Club/signup?email=test@mergington.edu")
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_duplicate_email():
    response = client.post("/activities/Chess Club/signup?email=michael@mergington.edu")
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"


# --- DELETE /activities/{name}/signup ---

def test_unregister_success():
    response = client.delete("/activities/Chess Club/signup?email=michael@mergington.edu")
    assert response.status_code == 200
    assert "michael@mergington.edu" in response.json()["message"]

    # Verify participant was removed
    activities_resp = client.get("/activities")
    assert "michael@mergington.edu" not in activities_resp.json()["Chess Club"]["participants"]


def test_unregister_activity_not_found():
    response = client.delete("/activities/Nonexistent Club/signup?email=test@mergington.edu")
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_email_not_found():
    response = client.delete("/activities/Chess Club/signup?email=nobody@mergington.edu")
    assert response.status_code == 400
    assert response.json()["detail"] == "Student is not signed up for this activity"


# --- Cross-endpoint integration ---

def test_signup_then_unregister():
    # Sign up
    signup_resp = client.post("/activities/Art Studio/signup?email=newartist@mergington.edu")
    assert signup_resp.status_code == 200

    # Verify added
    data = client.get("/activities").json()
    assert "newartist@mergington.edu" in data["Art Studio"]["participants"]

    # Unregister
    unreg_resp = client.delete("/activities/Art Studio/signup?email=newartist@mergington.edu")
    assert unreg_resp.status_code == 200

    # Verify removed
    data = client.get("/activities").json()
    assert "newartist@mergington.edu" not in data["Art Studio"]["participants"]
