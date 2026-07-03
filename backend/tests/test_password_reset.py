"""Self-service password reset via the security question."""
from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.config import settings
from app.models import User

# make_user seeds this question/answer pair on every account it creates.
QUESTION = "Favorite squadron?"
ANSWER = "695"


def test_forgot_password_returns_the_question(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user("amnesiac")
    resp = client.post("/api/v1/auth/forgot-password", json={"username": "amnesiac"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["secret_question"] == QUESTION


def test_forgot_password_accepts_email(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user("byemail")
    resp = client.post(
        "/api/v1/auth/forgot-password", json={"username": "byemail@det695.local"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["secret_question"] == QUESTION


def test_forgot_password_unknown_user_is_404(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/forgot-password", json={"username": "nobody"})
    assert resp.status_code == 404


def test_forgot_password_disabled_account_is_404(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user("benched", is_active=False)
    resp = client.post("/api/v1/auth/forgot-password", json={"username": "benched"})
    assert resp.status_code == 404


def test_reset_with_correct_answer_sets_new_password(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("forgetful", "OldPass123!")
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"username": "forgetful", "secret_answer": ANSWER, "new_password": "BrandNew123!"},
    )
    assert resp.status_code == 200, resp.text

    # Old password is dead; the new one works.
    assert login(client, "forgetful", "OldPass123!").status_code == 401
    assert login(client, "forgetful", "BrandNew123!").status_code == 200


def test_reset_tolerates_surrounding_whitespace_in_answer(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("spacey", "OldPass123!")
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={
            "username": "spacey",
            "secret_answer": f"  {ANSWER}  ",
            "new_password": "FreshPass123!",
        },
    )
    assert resp.status_code == 200, resp.text
    assert login(client, "spacey", "FreshPass123!").status_code == 200


def test_reset_with_wrong_answer_is_rejected(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("guarded", "OldPass123!")
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"username": "guarded", "secret_answer": "wrong", "new_password": "BrandNew123!"},
    )
    assert resp.status_code == 400
    # Password was not changed.
    assert login(client, "guarded", "OldPass123!").status_code == 200


def test_reset_min_length_is_enforced(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    make_user("shortreset")
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"username": "shortreset", "secret_answer": ANSWER, "new_password": "short"},
    )
    assert resp.status_code == 422  # schema rejects < 8 chars before the handler


def test_reset_unknown_user_is_400(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"username": "ghost", "secret_answer": ANSWER, "new_password": "Whatever123!"},
    )
    assert resp.status_code == 400


def test_wrong_answers_lock_then_correct_answer_unlocks(
    client: TestClient, make_user: Callable[..., User], login
) -> None:
    make_user("bruteme", "OldPass123!")

    # Enough wrong answers trip the same lockout as failed logins.
    for _ in range(settings.max_failed_logins):
        assert (
            client.post(
                "/api/v1/auth/reset-password",
                json={
                    "username": "bruteme",
                    "secret_answer": "nope",
                    "new_password": "BrandNew123!",
                },
            ).status_code
            == 400
        )
    # Locked out of login now.
    assert login(client, "bruteme", "OldPass123!").status_code == 403

    # The correct answer still resets and clears the lockout.
    resp = client.post(
        "/api/v1/auth/reset-password",
        json={"username": "bruteme", "secret_answer": ANSWER, "new_password": "BrandNew123!"},
    )
    assert resp.status_code == 200, resp.text
    assert login(client, "bruteme", "BrandNew123!").status_code == 200
