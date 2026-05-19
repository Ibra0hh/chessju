import pytest

from scripts.seed_demo_data import ensure_demo_seed_allowed
from scripts.smoke_test_api import SmokeStep, redact_sensitive_data


def test_demo_seed_allows_only_local_environments() -> None:
    for environment in ["development", "local", "test"]:
        ensure_demo_seed_allowed(environment)

    with pytest.raises(RuntimeError):
        ensure_demo_seed_allowed("production")


def test_smoke_redaction_removes_tokens_and_passwords() -> None:
    redacted = redact_sensitive_data(
        {
            "tokens": {
                "access_token": "access-secret",
                "refresh_token": "refresh-secret",
            },
            "password": "plain-password",
            "nested": [{"token_hash": "hash-secret", "safe": "visible"}],
        }
    )

    assert redacted["tokens"] == "[redacted]"
    assert redacted["password"] == "[redacted]"
    assert redacted["nested"][0]["token_hash"] == "[redacted]"
    assert redacted["nested"][0]["safe"] == "visible"
    assert "access-secret" not in str(redacted)
    assert "plain-password" not in str(redacted)


def test_smoke_step_details_can_be_token_safe() -> None:
    detail = str(redact_sensitive_data({"access_token": "secret", "message": "failed"}))
    step = SmokeStep(name="sample", status="FAIL", detail=detail)

    assert step.status == "FAIL"
    assert "secret" not in step.detail
    assert "[redacted]" in step.detail
