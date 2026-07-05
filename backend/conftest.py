"""Test helpers for the uniform response envelope.

Usage:
    from conftest import unwrap

    def test_something(client):
        resp = client.get("/api/state")
        data = unwrap(resp)  # returns resp.json()["data"], or raises on error
"""


def unwrap(response) -> dict:
    """Unwrap {ok, data, error} envelope. Asserts ok=True."""
    body = response.json()
    assert body.get("ok") is True, f"Response not ok: {body.get('error', 'unknown error')}"
    return body.get("data")
