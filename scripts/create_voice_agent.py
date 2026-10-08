import json
import os
from pathlib import Path

import httpx

AGENTS_URL = "https://agents.assemblyai.com/v1/agents"


def publish_agent(
    config: dict,
    api_key: str,
    agent_id: str | None = None,
    *,
    client=httpx,
) -> tuple[str, str]:
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    if agent_id:
        response = client.put(
            f"{AGENTS_URL}/{agent_id}",
            headers=headers,
            json=config,
            timeout=30,
        )
        action = "updated"
    else:
        response = client.post(
            AGENTS_URL,
            headers=headers,
            json=config,
            timeout=30,
        )
        action = "created"
    response.raise_for_status()
    body = response.json()
    published_id = body.get("id") or body.get("agent_id") or agent_id
    if not published_id:
        raise RuntimeError("AssemblyAI response did not include an agent ID")
    return str(published_id), action


def main() -> None:
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise SystemExit("ASSEMBLYAI_API_KEY is required")
    config_path = Path(__file__).parents[1] / "assemblyai" / "agent.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    agent_id, action = publish_agent(
        config,
        api_key,
        os.getenv("ASSEMBLYAI_AGENT_ID") or None,
    )
    print(f"Agent {action}: {agent_id}")


if __name__ == "__main__":
    main()
