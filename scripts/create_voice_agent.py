import json
import os
from pathlib import Path

import httpx


def main() -> None:
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise SystemExit("ASSEMBLYAI_API_KEY is required")
    config_path = Path(__file__).parents[1] / "assemblyai" / "agent.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    response = httpx.post(
        "https://agents.assemblyai.com/v1/agents",
        headers={"Authorization": api_key, "Content-Type": "application/json"},
        json=config,
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    print(body.get("id") or body.get("agent_id"))


if __name__ == "__main__":
    main()
