import app.services.email as email


def test_build_2fa_code_email_contains_code() -> None:
    subject, body = email.build_2fa_code_email("246810")
    assert "246810" in body
    assert "code" in subject.lower()


def test_send_2fa_code_delegates(monkeypatch) -> None:
    captured = {}

    def fake_send(to, subject, body):
        captured.update(to=to, subject=subject, body=body)
        return True

    monkeypatch.setattr(email, "send_email", fake_send)
    assert email.send_2fa_code("u@example.com", "135791") is True
    assert captured["to"] == "u@example.com"
    assert "135791" in captured["body"]
