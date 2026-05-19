from __future__ import annotations

import argparse
import json
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

DEMO_PGN = """[Event "ChessJU Smoke Game"]
[Site "Local QA"]
[Date "2026.05.19"]
[Round "1"]
[White "Smoke White"]
[Black "Smoke Black"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

SENSITIVE_KEYS = {
    "access_token",
    "refresh_token",
    "token",
    "tokens",
    "password",
    "password_hash",
    "token_hash",
    "authorization",
}


@dataclass(frozen=True)
class SmokeStep:
    name: str
    status: str
    detail: str = ""


def redact_sensitive_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if key.lower() in SENSITIVE_KEYS else redact_sensitive_data(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]
    return value


class SmokeApi:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=20)

    def close(self) -> None:
        self.client.close()

    def public_url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def api_url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: dict[str, Any] | None = None,
        expected: set[int] | None = None,
        api: bool = True,
    ) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        url = self.api_url(path) if api else self.public_url(path)
        response = self.client.request(method, url, json=json_body, headers=headers)
        expected_statuses = expected or {200}
        if response.status_code not in expected_statuses:
            body = response.text[:600]
            try:
                body = json.dumps(redact_sensitive_data(response.json()))
            except ValueError:
                pass
            raise RuntimeError(f"{method} {path} returned {response.status_code}: {body}")
        if not response.content:
            return None
        return response.json()


def _user_payload(prefix: str) -> dict[str, str]:
    suffix = uuid.uuid4().hex[:10]
    return {
        "email": f"{prefix}-{suffix}@example.com",
        "password": "SmokeTest123!",
        "username": f"{prefix}_{suffix}",
        "full_name": f"{prefix.replace('_', ' ').title()} User",
    }


def _register(api: SmokeApi, prefix: str) -> dict[str, Any]:
    payload = _user_payload(prefix)
    return api.request("POST", "/auth/register", json_body=payload, expected={201})


def _login(api: SmokeApi, email: str, password: str) -> dict[str, Any]:
    return api.request(
        "POST",
        "/auth/login",
        json_body={"email": email, "password": password},
        expected={200},
    )


def _run_step(steps: list[SmokeStep], name: str, action: Any) -> Any:
    try:
        result = action()
    except Exception as exc:  # noqa: BLE001 - script should continue and report all failures.
        steps.append(
            SmokeStep(name=name, status="FAIL", detail=str(redact_sensitive_data(str(exc))))
        )
        return None
    steps.append(SmokeStep(name=name, status="PASS"))
    return result


def _skip(steps: list[SmokeStep], name: str, reason: str) -> None:
    steps.append(SmokeStep(name=name, status="SKIP", detail=reason))


def run_smoke(
    *,
    base_url: str,
    member_email: str | None = None,
    member_password: str | None = None,
    friend_email: str | None = None,
    friend_password: str | None = None,
    admin_email: str | None = None,
    admin_password: str | None = None,
) -> list[SmokeStep]:
    api = SmokeApi(base_url)
    steps: list[SmokeStep] = []
    try:
        for path in ["/health", "/version", "/health/db", "/health/valkey"]:
            _run_step(steps, f"GET {path}", lambda path=path: api.request("GET", path, api=False))

        if member_email and member_password:
            user_one = _run_step(
                steps,
                "login member one",
                lambda: _login(api, member_email, member_password),
            )
        else:
            user_one = _run_step(
                steps,
                "register member one",
                lambda: _register(api, "smoke_member"),
            )
        if friend_email and friend_password:
            user_two = _run_step(
                steps,
                "login member two",
                lambda: _login(api, friend_email, friend_password),
            )
        else:
            user_two = _run_step(
                steps,
                "register member two",
                lambda: _register(api, "smoke_friend"),
            )
        if not user_one or not user_two:
            return steps

        member_token = user_one["tokens"]["access_token"]
        friend_token = user_two["tokens"]["access_token"]
        if not member_email:
            _run_step(
                steps,
                "login member one",
                lambda: _login(api, user_one["user"]["email"], "SmokeTest123!"),
            )
        _run_step(steps, "GET /home", lambda: api.request("GET", "/home"))
        _run_step(steps, "GET /news", lambda: api.request("GET", "/news"))
        _run_step(steps, "GET /tournaments", lambda: api.request("GET", "/tournaments"))
        _run_step(steps, "GET /leaderboard", lambda: api.request("GET", "/leaderboard"))
        _run_step(
            steps,
            "GET Chess.com account",
            lambda: api.request("GET", "/integrations/chesscom/account", token=member_token),
        )

        game = _run_step(
            steps,
            "paste PGN",
            lambda: api.request(
                "POST",
                "/games/pgn/paste",
                token=member_token,
                json_body={"pgn_text": DEMO_PGN},
                expected={200, 201},
            ),
        )
        if game:
            _run_step(
                steps,
                "request analysis",
                lambda: api.request(
                    "POST",
                    f"/games/{game['id']}/analysis",
                    token=member_token,
                    json_body={"depth": 1},
                    expected={200, 201},
                ),
            )

        clock = _run_step(
            steps,
            "create clock",
            lambda: api.request(
                "POST",
                "/clock/sessions",
                token=member_token,
                json_body={"base_seconds": 300, "increment_seconds": 0, "delay_seconds": 0},
                expected={201},
            ),
        )
        if clock:
            session_id = clock["id"]
            start_body = {
                "white_remaining_ms": 300000,
                "black_remaining_ms": 300000,
                "active_color": "white",
            }
            switch_body = {
                "white_remaining_ms": 299000,
                "black_remaining_ms": 300000,
                "active_color": "black",
            }
            complete_body = {
                "white_remaining_ms": 299000,
                "black_remaining_ms": 299000,
                "result": "draw",
            }
            _run_step(
                steps,
                "start clock",
                lambda: api.request(
                    "POST",
                    f"/clock/sessions/{session_id}/start",
                    token=member_token,
                    json_body=start_body,
                ),
            )
            _run_step(
                steps,
                "switch clock turn",
                lambda: api.request(
                    "POST",
                    f"/clock/sessions/{session_id}/switch-turn",
                    token=member_token,
                    json_body=switch_body,
                ),
            )
            _run_step(
                steps,
                "complete clock",
                lambda: api.request(
                    "POST",
                    f"/clock/sessions/{session_id}/complete",
                    token=member_token,
                    json_body=complete_body,
                ),
            )

        friend_request = _run_step(
            steps,
            "send friend request",
            lambda: api.request(
                "POST",
                "/friends/requests",
                token=member_token,
                json_body={"receiver_id": user_two["user"]["id"]},
                expected={201, 409},
            ),
        )
        if friend_request:
            if "id" in friend_request:
                _run_step(
                    steps,
                    "accept friend request",
                    lambda: api.request(
                        "POST",
                        f"/friends/requests/{friend_request['id']}/accept",
                        token=friend_token,
                    ),
                )
            else:
                _skip(
                    steps,
                    "accept friend request",
                    "friend request already exists or users are connected",
                )
            conversation = _run_step(
                steps,
                "create direct conversation",
                lambda: api.request(
                    "POST",
                    "/conversations/direct",
                    token=member_token,
                    json_body={"user_id": user_two["user"]["id"]},
                    expected={200, 201},
                ),
            )
            if conversation:
                _run_step(
                    steps,
                    "send direct message",
                    lambda: api.request(
                        "POST",
                        f"/conversations/{conversation['id']}/messages",
                        token=member_token,
                        json_body={"body": "Smoke test hello"},
                        expected={200, 201},
                    ),
                )
        _run_step(
            steps,
            "notifications unread count",
            lambda: api.request("GET", "/notifications/unread-count", token=friend_token),
        )

        if admin_email and admin_password:
            admin_login = _run_step(
                steps,
                "login admin",
                lambda: _login(api, admin_email, admin_password),
            )
            if admin_login:
                admin_token = admin_login["tokens"]["access_token"]
                _run_step(
                    steps,
                    "GET /admin/me",
                    lambda: api.request("GET", "/admin/me", token=admin_token),
                )
                _run_step(
                    steps,
                    "GET admin audit logs",
                    lambda: api.request("GET", "/admin/audit-logs", token=admin_token),
                )
        else:
            _skip(steps, "admin flows", "provide --admin-email and --admin-password")
    finally:
        api.close()
    return steps


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ChessJU local API smoke checks.")
    parser.add_argument("--base-url", default="http://localhost:8001")
    parser.add_argument("--member-email")
    parser.add_argument("--member-password")
    parser.add_argument("--friend-email")
    parser.add_argument("--friend-password")
    parser.add_argument("--admin-email")
    parser.add_argument("--admin-password")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    steps = run_smoke(
        base_url=args.base_url,
        member_email=args.member_email,
        member_password=args.member_password,
        friend_email=args.friend_email,
        friend_password=args.friend_password,
        admin_email=args.admin_email,
        admin_password=args.admin_password,
    )
    for step in steps:
        suffix = f" - {step.detail}" if step.detail else ""
        print(f"[{step.status}] {step.name}{suffix}")
    failures = [step for step in steps if step.status == "FAIL"]
    print(f"Smoke checks: {len(steps) - len(failures)}/{len(steps)} non-failing")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
