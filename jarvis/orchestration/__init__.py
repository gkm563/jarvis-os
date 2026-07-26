"""
Orchestration Package Initialization.
"""

from jarvis.orchestration.state_machine import PlanStateMachine
from jarvis.orchestration.executor import ExecutionManager, AgentRegistry, agent_registry
from jarvis.orchestration.queue import TaskExecutionQueue

execution_manager = ExecutionManager(registry=agent_registry)
task_queue = TaskExecutionQueue(executor=execution_manager)

__all__ = [
    "PlanStateMachine",
    "ExecutionManager",
    "AgentRegistry",
    "agent_registry",
    "execution_manager",
    "TaskExecutionQueue",
    "task_queue",
]
