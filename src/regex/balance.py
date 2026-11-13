"""Read account credits without exposing the API key or HTTP error bodies."""
import json
import os
from datetime import datetime, timezone

import httpx

from src.pipeline.runner import PROJECT_ROOT


def main():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is missing from GitHub Actions secrets")
    with httpx.Client(timeout=30) as client:
        response = client.get("https://openrouter.ai/api/v1/credits", headers={"Authorization": f"Bearer {key}"})
    if response.status_code != 200:
        raise SystemExit(f"balance check failed: HTTP {response.status_code}")
    data = response.json()["data"]
    report = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "total_credits_usd": data["total_credits"], "total_usage_usd": data["total_usage"],
              "remaining_usd": data["total_credits"] - data["total_usage"]}
    (PROJECT_ROOT / "reports/openrouter_balance.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
