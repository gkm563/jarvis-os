"""
Unit Tests for File System Agent CRUD, Duplicate Scanner, and Backup.
"""

import pytest
from pathlib import Path
from jarvis.agents.file_agent import FileSystemAgent
from jarvis.core.models import AgentAction


@pytest.mark.asyncio
async def test_file_agent_write_and_read(tmp_path):
    agent = FileSystemAgent()
    test_file = tmp_path / "sample.txt"

    # Write file
    write_action = AgentAction(
        agent_name="file_agent",
        action_type="write_file",
        parameters={"filepath": str(test_file), "content": "Hello JARVIS OS"},
    )
    write_res = await agent.execute(write_action)
    assert write_res.success is True

    # Read file
    read_action = AgentAction(
        agent_name="file_agent",
        action_type="read_file",
        parameters={"filepath": str(test_file)},
    )
    read_res = await agent.execute(read_action)
    assert read_res.success is True
    assert read_res.data["content"] == "Hello JARVIS OS"


@pytest.mark.asyncio
async def test_file_agent_duplicate_scan(tmp_path):
    agent = FileSystemAgent()
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("Identical Content", encoding="utf-8")
    f2.write_text("Identical Content", encoding="utf-8")

    scan_action = AgentAction(
        agent_name="file_agent",
        action_type="duplicate_scan",
        parameters={"target_path": str(tmp_path)},
    )
    res = await agent.execute(scan_action)
    assert res.success is True
    assert res.data["set_count"] == 1
