"""
Unit Tests for Task Planner and DAG Cycle Validator.
"""

import pytest
from jarvis.brain.planner import TaskPlanner
from jarvis.core.models import Plan, Step, AgentAction
from jarvis.core.exceptions import PlanningError


@pytest.mark.asyncio
async def test_planner_creates_valid_dag():
    planner = TaskPlanner()
    plan = await planner.create_plan("Open Chrome and download result")
    assert plan is not None
    assert len(plan.steps) > 0
    assert plan.user_goal == "Open Chrome and download result"


def test_planner_detects_dag_cycle():
    planner = TaskPlanner()
    cyclic_plan = Plan(
        plan_id="cyclic_plan",
        user_goal="Invalid cycle task",
        steps=[
            Step(
                step_id="step_1",
                description="Step 1",
                action=AgentAction(agent_name="desktop_agent", action_type="launch_app"),
                dependencies=["step_2"],
            ),
            Step(
                step_id="step_2",
                description="Step 2",
                action=AgentAction(agent_name="desktop_agent", action_type="launch_app"),
                dependencies=["step_1"],
            ),
        ],
    )

    with pytest.raises(PlanningError, match="Circular dependency cycle detected"):
        planner.validate_dag(cyclic_plan)
