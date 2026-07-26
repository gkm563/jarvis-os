"""
Integration Tests for Task Execution Manager and DAG Orchestration.
"""

import pytest
from jarvis.orchestration.executor import ExecutionManager, AgentRegistry
from jarvis.agents.desktop_agent import DesktopControlAgent
from jarvis.agents.file_agent import FileSystemAgent
from jarvis.core.models import Plan, Step, AgentAction, PlanStatus


@pytest.mark.asyncio
async def test_orchestrator_executes_plan_dag(tmp_path):
    registry = AgentRegistry()
    registry.register(DesktopControlAgent())
    registry.register(FileSystemAgent())

    executor = ExecutionManager(registry=registry)

    test_file = tmp_path / "plan_test.txt"

    plan = Plan(
        plan_id="integration_plan_1",
        user_goal="Launch app and write test file",
        steps=[
            Step(
                step_id="step_1",
                description="Launch App",
                action=AgentAction(
                    agent_name="desktop_agent",
                    action_type="launch_app",
                    parameters={"app_name": "notepad"},
                ),
            ),
            Step(
                step_id="step_2",
                description="Write File",
                action=AgentAction(
                    agent_name="file_agent",
                    action_type="write_file",
                    parameters={"filepath": str(test_file), "content": "Integration Test Passed"},
                ),
                dependencies=["step_1"],
            ),
        ],
    )

    result_plan = await executor.execute_plan(plan)
    assert result_plan.status == PlanStatus.COMPLETED
    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == "Integration Test Passed"
