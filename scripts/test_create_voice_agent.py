from unittest.mock import Mock

from scripts.create_voice_agent import publish_agent


def response(agent_id: str) -> Mock:
    result = Mock()
    result.json.return_value = {"id": agent_id}
    return result


def test_publish_creates_agent_when_id_is_missing():
    client = Mock()
    client.post.return_value = response("agent-new")

    agent_id, action = publish_agent(
        {"name": "BizExpense Voice"}, "secret-key", client=client
    )

    assert (agent_id, action) == ("agent-new", "created")
    client.post.assert_called_once_with(
        "https://agents.assemblyai.com/v1/agents",
        headers={"Authorization": "secret-key", "Content-Type": "application/json"},
        json={"name": "BizExpense Voice"},
        timeout=30,
    )
    client.put.assert_not_called()


def test_publish_updates_configured_agent():
    client = Mock()
    client.put.return_value = response("agent-existing")

    agent_id, action = publish_agent(
        {"name": "BizExpense Voice"},
        "secret-key",
        agent_id="agent-existing",
        client=client,
    )

    assert (agent_id, action) == ("agent-existing", "updated")
    client.put.assert_called_once_with(
        "https://agents.assemblyai.com/v1/agents/agent-existing",
        headers={"Authorization": "secret-key", "Content-Type": "application/json"},
        json={"name": "BizExpense Voice"},
        timeout=30,
    )
    client.post.assert_not_called()
