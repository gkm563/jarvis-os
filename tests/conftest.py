"""
Pytest Test Suite Configuration and Shared Fixtures for JARVIS OS.
"""

import pytest
import asyncio
from jarvis.security.vault import AESVault
from jarvis.memory.short_term import ShortTermMemory
from jarvis.memory.long_term import LongTermMemory
from jarvis.orchestration.executor import ExecutionManager, AgentRegistry
from jarvis.agents.file_agent import FileSystemAgent
from jarvis.agents.desktop_agent import DesktopControlAgent


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def vault():
    return AESVault(master_password="test-master-password-12345")


@pytest.fixture
def short_memory():
    return ShortTermMemory()


@pytest.fixture
def long_memory(tmp_path):
    db_file = tmp_path / "test_jarvis.db"
    return LongTermMemory(db_url=f"sqlite:///{db_file}")


@pytest.fixture
def test_registry():
    registry = AgentRegistry()
    registry.register(FileSystemAgent())
    registry.register(DesktopControlAgent())
    return registry


@pytest.fixture
def executor(test_registry):
    return ExecutionManager(registry=test_registry)
