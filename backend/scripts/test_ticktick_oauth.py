"""Manual TickTick OAuth test helper.

This script exists purely for debugging the TickTick integration outside of the
main FastAPI app. It replicates the four OAuth steps:

1. Print the authorization URL so you can open it in a browser.
2. Wait for you to paste the ``code`` parameter returned by TickTick.
3. Exchange the code for an access token using the same request the backend
   issues (including Basic Auth and scope handling).
4. Pretty print the JSON payload returned by TickTick.

Usage
-----

```bash
python backend/scripts/test_ticktick_oauth.py \
  --client-id "$TICKTICK_CLIENT_ID" \
  --client-secret "$TICKTICK_CLIENT_SECRET" \
  --redirect-uri "http://localhost:8000/api/ticktick/callback"
```

If you omit the CLI arguments the script falls back to the values defined in
``app.config.settings`` so it will respect your local ``.env`` file.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode, quote

import httpx

try:  # Lazy import so the script still runs even if app dependencies are absent
    from app.config import settings  # type: ignore
except Exception:  # pragma: no cover - defensive fallback when running standalone
    settings = None  # type: ignore


DEFAULT_SCOPE = "tasks:write tasks:read"


@dataclass
class TickTickCredentials:
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = DEFAULT_SCOPE


def build_authorization_url(creds: TickTickCredentials, state: str) -> str:
    params = {
        "client_id": creds.client_id,
        "redirect_uri": creds.redirect_uri,
        "response_type": "code",
        "scope": creds.scope,
        "state": state,
    }
    return f"https://ticktick.com/oauth/authorize?{urlencode(params)}"


async def exchange_code_for_token(
    creds: TickTickCredentials, code: str
) -> dict[str, Any]:
    """Perform the code → token exchange against TickTick."""

    encoded_client_id = quote(creds.client_id, safe="")
    encoded_client_secret = quote(creds.client_secret, safe="")
    basic_token = base64.b64encode(
        f"{encoded_client_id}:{encoded_client_secret}".encode("utf-8")
    ).decode("utf-8")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {basic_token}",
    }
    data = {
        "code": code,
        "redirect_uri": creds.redirect_uri,
        "grant_type": "authorization_code",
        "scope": creds.scope,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://ticktick.com/oauth/token", data=data, headers=headers
        )
        print("\n=== Raw Response ===")
        print(f"Status: {response.status_code}")
        print(response.text)
        response.raise_for_status()
        return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manual TickTick OAuth tester")
    parser.add_argument("--client-id", dest="client_id", help="TickTick client ID")
    parser.add_argument(
        "--client-secret", dest="client_secret", help="TickTick client secret"
    )
    parser.add_argument(
        "--redirect-uri",
        dest="redirect_uri",
        default="http://localhost:8000/api/ticktick/callback",
        help="OAuth redirect URI (defaults to local API callback)",
    )
    parser.add_argument(
        "--scope",
        dest="scope",
        default=DEFAULT_SCOPE,
        help="OAuth scope string (default: tasks:write tasks:read)",
    )

    args = parser.parse_args()

    client_id = args.client_id or getattr(settings, "ticktick_client_id", None)
    client_secret = args.client_secret or getattr(
        settings, "ticktick_client_secret", None
    )
    if not client_id or not client_secret:
        raise SystemExit(
            "TickTick client ID/secret are required. Pass --client-id/--client-secret "
            "or set them in your environment/.env file."
        )

    creds = TickTickCredentials(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=args.redirect_uri,
        scope=args.scope,
    )

    state = "manual_test"
    auth_url = build_authorization_url(creds, state)
    print("\n=== Step 1: Authorize the app ===")
    print("Open this URL in your browser, approve access, then copy the 'code' value:")
    print(auth_url)

    code = input("\nPaste the authorization code here: ").strip()
    if not code:
        raise SystemExit("No authorization code provided.")

    print("\n=== Step 3: Exchanging code for token ===")
    token_payload = asyncio.run(exchange_code_for_token(creds, code))

    print("\n=== Parsed Token Payload ===")
    print(json.dumps(token_payload, indent=2))


if __name__ == "__main__":
    main()
