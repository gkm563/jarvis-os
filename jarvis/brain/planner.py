"""
Multi-Agent DAG Task Planner for JARVIS OS.
Decomposes natural language user goals into structured Directed Acyclic Graph (DAG) plans.
"""

from typing import Dict, List, Set, Optional
from jarvis.core.models import Plan, Step, PlanStatus
from jarvis.core.exceptions import PlanningError
from jarvis.brain.llm_provider import UniversalLLMProvider
from jarvis.utils.logger import get_logger

logger = get_logger("TaskPlanner")


class TaskPlanner:
    """
    Decomposes instructions into ordered execution DAGs with strict cycle validation.
    """

    def __init__(self, llm_provider: Optional[UniversalLLMProvider] = None):
        self.llm_provider = llm_provider or UniversalLLMProvider()

    async def create_plan(self, user_goal: str, context: Optional[str] = None) -> Plan:
        """
        Creates and validates an execution plan DAG from a user goal.

        Args:
            user_goal (str): Natural language task prompt.
            context (Optional[str]): Environment context.

        Returns:
            Plan: Validated execution plan DAG.
        """
        if not user_goal or not user_goal.strip():
            raise PlanningError("User goal cannot be empty")

        logger.info(f"Decomposing user goal into DAG plan: '{user_goal}'")
        plan = await self.llm_provider.generate_plan(user_goal, context)

        # Validate DAG structure for cycles
        self.validate_dag(plan)

        logger.info(f"Plan '{plan.plan_id}' successfully constructed with {len(plan.steps)} steps")
        return plan

    def validate_dag(self, plan: Plan) -> None:
        """
        Verifies that step dependencies form a valid Directed Acyclic Graph (no cycles).

        Args:
            plan (Plan): Generated plan object.

        Raises:
            PlanningError: If a cycle or missing dependency step is detected.
        """
        step_ids = {s.step_id for s in plan.steps}

        # Check for missing dependency references
        for step in plan.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    raise PlanningError(
                        f"Invalid DAG: Step '{step.step_id}' references unknown dependency '{dep}'"
                    )

        # Cycle detection using depth-first search (Kahn's algorithm)
        in_degree = {s.step_id: 0 for s in plan.steps}
        adj = {s.step_id: [] for s in plan.steps}

        for step in plan.steps:
            for dep in step.dependencies:
                adj[dep].append(step.step_id)
                in_degree[step.step_id] += 1

        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        visited_count = 0

        while queue:
            node = queue.pop(0)
            visited_count += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(plan.steps):
            raise PlanningError("Invalid DAG: Circular dependency cycle detected in plan steps")
