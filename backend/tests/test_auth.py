"""Auth flow: signup, login, and that protected routes reject requests
with no token, a garbage token, but accept a valid one. Also covers the
two password-handling fixes from the security review: an over-length
password must not crash bcrypt, and a rejected password must never be
echoed back in a validation error.
"""


def test_signup_returns_token(client, make_email, test_password):
    res = client.post("/auth/signup", json={"email": make_email(), "password": test_password})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_signup_duplicate_email_rejected(client, make_email, test_password):
    email = make_email()
    first = client.post("/auth/signup", json={"email": email, "password": test_password})
    assert first.status_code == 200
    second = client.post("/auth/signup", json={"email": email, "password": test_password})
    assert second.status_code == 409


def test_signup_weak_password_rejected(client, make_email):
    res = client.post("/auth/signup", json={"email": make_email(), "password": "short"})
    assert res.status_code == 422


def test_signup_invalid_email_rejected(client, test_password):
    res = client.post("/auth/signup", json={"email": "not-an-email", "password": test_password})
    assert res.status_code == 422


def test_login_success(client, make_email, test_password):
    email = make_email()
    client.post("/auth/signup", json={"email": email, "password": test_password})
    res = client.post("/auth/login", json={"email": email, "password": test_password})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password_rejected(client, make_email, test_password):
    email = make_email()
    client.post("/auth/signup", json={"email": email, "password": test_password})
    res = client.post("/auth/login", json={"email": email, "password": "wrong-password"})
    assert res.status_code == 401


def test_login_unknown_email_rejected(client, make_email, test_password):
    res = client.post("/auth/login", json={"email": make_email(), "password": test_password})
    assert res.status_code == 401


def test_protected_routes_reject_missing_token(client):
    assert client.get("/transactions").status_code == 401
    assert client.post("/transactions", json={}).status_code == 401
    assert client.patch("/transactions/1", json={"status": "cleared"}).status_code == 401
    assert client.post("/seed-demo-data").status_code == 401


def test_protected_route_rejects_garbage_token(client):
    res = client.get("/transactions", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_protected_route_accepts_valid_token(client, auth_headers):
    res = client.get("/transactions", headers=auth_headers)
    assert res.status_code == 200


def test_overlong_password_rejected_not_500(client, make_email):
    res = client.post("/auth/signup", json={"email": make_email(), "password": "a" * 100})
    assert res.status_code == 422


def test_overlong_password_rejected_on_login_not_500(client, make_email, test_password):
    email = make_email()
    client.post("/auth/signup", json={"email": email, "password": test_password})
    res = client.post("/auth/login", json={"email": email, "password": "a" * 100})
    assert res.status_code == 422


def test_password_not_echoed_in_validation_error(client, make_email):
    # Deliberately not "short" — that string is also a substring of the
    # Pydantic error *type*, "string_too_short", which would make the
    # assertion below pass even if the raw password leaked back out.
    weak_password = "abc123"
    res = client.post("/auth/signup", json={"email": make_email(), "password": weak_password})
    assert res.status_code == 422
    assert weak_password not in res.text
    assert '"input":"[redacted]"' in res.text
