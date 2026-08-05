"""
Unit tests for JARVIS OS Domain Agents (Desktop, Browser, Coding, Email, Office, Developer, Database, Scheduler, Research).
"""

import pytest
from jarvis.core.models import AgentAction
from jarvis.agents.desktop_agent import DesktopControlAgent
from jarvis.agents.browser_agent import BrowserAutomationAgent
from jarvis.agents.coding_agent import AICodingAgent
from jarvis.agents.email_agent import EmailAgent
from jarvis.agents.office_agent import OfficeAgent
from jarvis.agents.developer_agent import DeveloperAgent
from jarvis.agents.database_agent import DatabaseAgent
from jarvis.agents.scheduler_agent import SchedulerAgent
from jarvis.agents.research_agent import InternetResearchAgent


@pytest.mark.asyncio
async def test_desktop_agent_launch_and_snap():
    agent = DesktopControlAgent()
    action = AgentAction(
        agent_name="desktop_agent",
        action_type="launch_app",
        parameters={"app_name": "notepad"},
    )
    result = await agent.execute(action)
    assert result.success is True
    assert result.data["app_name"] == "notepad"

    snap_action = AgentAction(
        agent_name="desktop_agent",
        action_type="snap_window",
        parameters={"window_title": "Notepad", "position": "left"},
    )
    snap_res = await agent.execute(snap_action)
    assert snap_res.success is True
    assert snap_res.data["position"] == "left"


@pytest.mark.asyncio
async def test_browser_agent_navigate():
    agent = BrowserAutomationAgent()
    action = AgentAction(
        agent_name="browser_agent",
        action_type="navigate",
        parameters={"url": "https://google.com", "query": "search AKTU results"},
    )
    result = await agent.execute(action)
    assert result.success is True
    assert "url" in result.data


@pytest.mark.asyncio
async def test_email_agent_send_and_summarize():
    agent = EmailAgent()
    send_action = AgentAction(
        agent_name="email_agent",
        action_type="send_email",
        parameters={"recipient": "user@example.com", "subject": "Test", "body": "Hello"},
    )
    res = await agent.execute(send_action)
    assert res.success is True
    assert res.data["status"] == "sent"

    sum_action = AgentAction(
        agent_name="email_agent",
        action_type="summarize_inbox",
        parameters={},
    )
    sum_res = await agent.execute(sum_action)
    assert sum_res.success is True
    assert sum_res.data["unread_count"] > 0


@pytest.mark.asyncio
async def test_office_agent_create_doc():
    agent = OfficeAgent()
    action = AgentAction(
        agent_name="office_agent",
        action_type="create_doc",
        parameters={"filepath": "./test_doc.docx", "content": "Test Content"},
    )
    res = await agent.execute(action)
    assert res.success is True
    assert "filepath" in res.data


@pytest.mark.asyncio
async def test_developer_agent_terminal_cmd():
    agent = DeveloperAgent()
    action = AgentAction(
        agent_name="developer_agent",
        action_type="terminal_command",
        parameters={"command": "echo JARVIS_TEST"},
    )
    res = await agent.execute(action)
    assert res.success is True
    assert "JARVIS_TEST" in res.data["stdout"]


@pytest.mark.asyncio
async def test_database_agent_query():
    agent = DatabaseAgent()
    action = AgentAction(
        agent_name="database_agent",
        action_type="query_db",
        parameters={"db_path": "jarvis_data.db", "query": "SELECT 1;"},
    )
    res = await agent.execute(action)
    assert res.success is True


@pytest.mark.asyncio
async def test_scheduler_agent_add_event():
    agent = SchedulerAgent()
    action = AgentAction(
        agent_name="scheduler_agent",
        action_type="add_event",
        parameters={"title": "Team Meeting", "time": "Tomorrow 10:00 AM"},
    )
    res = await agent.execute(action)
    assert res.success is True
    assert res.data["status"] == "scheduled"


@pytest.mark.asyncio
async def test_research_agent_deep_research():
    agent = InternetResearchAgent()
    action = AgentAction(
        agent_name="research_agent",
        action_type="deep_research",
        parameters={"topic": "Quantum Computing", "depth": 2},
    )
    res = await agent.execute(action)
    assert res.success is True
    assert len(res.data["findings"]) > 0
