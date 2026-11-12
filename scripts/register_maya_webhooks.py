"""
Register Maya Checkout sandbox webhooks for this OneGov PH instance.

Usage (from project root):

  MAYA_WEBHOOK_BASE_URL=https://your-public-https-host \\
    python scripts/register_maya_webhooks.py

Maya requires a publicly reachable HTTPS URL. Localhost alone will not receive
webhooks — use a tunnel such as ngrok, then set MAYA_WEBHOOK_BASE_URL.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_app():
    spec = importlib.util.spec_from_file_location("onegov_flask_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.create_app()


def main() -> int:
    application = _load_app()
    from app.services.maya_checkout import MayaCheckoutError, ensure_webhooks

    with application.app_context():
        base = (
            os.getenv("MAYA_WEBHOOK_BASE_URL")
            or application.config.get("MAYA_WEBHOOK_BASE_URL")
            or ""
        ).strip().rstrip("/")
        if not base.startswith("https://"):
            print(
                "Set MAYA_WEBHOOK_BASE_URL to a public HTTPS origin "
                "(example: https://abc123.ngrok-free.app).",
                file=sys.stderr,
            )
            return 1
        callback = f"{base}/webhooks/maya"
        try:
            results = ensure_webhooks(callback)
        except MayaCheckoutError as exc:
            print(f"Webhook registration failed: {exc}", file=sys.stderr)
            return 1
        print(f"Registered/confirmed webhooks → {callback}")
        for item in results:
            print(f"  - {item.get('name')}: {item.get('id')} ({item.get('callbackUrl')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
