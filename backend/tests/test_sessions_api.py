def _login(client, make_user, name="rr"):
    make_user(name, "Recruit123!")
    r = client.post("/api/v1/auth/login", json={"username": name, "password": "Recruit123!"})
    j = r.json()
    return {"Authorization": f"Bearer {j['access_token']}"}


def test_list_sessions_marks_current_and_hides_sid(client, make_user):
    h = _login(client, make_user)
    r = client.get("/api/v1/profile/sessions", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["current"] is True
    assert "sid" not in rows[0]


def test_revoke_other_session_signs_it_out(client, make_user):
    h1 = _login(client, make_user, "userA")
    # a second login for the same user = a second session
    r2 = client.post("/api/v1/auth/login", json={"username": "userA", "password": "Recruit123!"})
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    rows = client.get("/api/v1/profile/sessions", headers=h1).json()
    other = next(s for s in rows if not s["current"])
    assert client.delete(f"/api/v1/profile/sessions/{other['id']}", headers=h1).status_code == 200
    # the revoked session's token is now dead
    assert client.get("/api/v1/auth/me", headers=h2).status_code == 401


def test_cannot_revoke_another_users_session(client, make_user):
    h1 = _login(client, make_user, "owner")
    hx = _login(client, make_user, "intruder")
    sid_row = client.get("/api/v1/profile/sessions", headers=h1).json()[0]
    assert client.delete(f"/api/v1/profile/sessions/{sid_row['id']}", headers=hx).status_code == 404


def test_revoke_others_keeps_current(client, make_user):
    h1 = _login(client, make_user, "multi")
    client.post("/api/v1/auth/login", json={"username": "multi", "password": "Recruit123!"})
    client.post("/api/v1/auth/login", json={"username": "multi", "password": "Recruit123!"})
    r = client.post("/api/v1/profile/sessions/revoke-others", headers=h1)
    assert r.status_code == 200
    rows = client.get("/api/v1/profile/sessions", headers=h1).json()
    assert len(rows) == 1 and rows[0]["current"] is True
