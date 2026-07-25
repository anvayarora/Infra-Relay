from datetime import datetime, timedelta, timezone


def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_resource_booking_conflict(client, auth):
    resource = client.post(
        "/api/v1/resources",
        headers=auth,
        json={"name": "GPU 1", "resource_type": "gpu_server", "booking_policy": {"bookable": True}},
    ).get_json()
    start = datetime.now(timezone.utc) + timedelta(days=1)
    payload = {
        "resource_id": resource["id"],
        "requested_by": "engineer@test.local",
        "purpose": "GPU lab",
        "starts_at": start.isoformat(),
        "ends_at": (start + timedelta(hours=2)).isoformat(),
    }
    assert client.post("/api/v1/bookings", headers=auth, json=payload).status_code == 201
    assert client.post("/api/v1/bookings", headers=auth, json=payload).status_code == 409


def test_credential_secret_is_not_returned(client, auth):
    response = client.post(
        "/api/v1/credentials",
        headers=auth,
        json={
            "name": "Corporate AD",
            "kind": "ldap",
            "metadata": {"host": "10.0.0.2", "base_dn": "DC=example,DC=com"},
            "secrets": {"username": "svc", "password": "secret"},
        },
    )
    body = response.get_json()
    assert response.status_code == 201
    assert body["kind"] == "ldap"
    assert "password" not in str(body)
    assert "secret" not in str(body)
