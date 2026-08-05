"""
FastAPI Endpoint for Natural Language Intent Processing and Plan Retrieval.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from jarvis.brain.planner import TaskPlanner
from jarvis.orchestration.executor import ExecutionManager
from jarvis.core.models import Plan, PlanStatus
from jarvis.utils.logger import get_logger

logger = get_logger("API_Intent")
router = APIRouter(prefix="/v1", tags=["Intent & Planning"])

planner = TaskPlanner()
executor = ExecutionManager()

# In-memory plan cache for status queries
active_plans: Dict[str, Plan] = {}


class IntentRequest(BaseModel):
    user_goal: str
    context: Optional[str] = None
    execute_immediately: bool = True


class IntentResponse(BaseModel):
    plan_id: str
    user_goal: str
    status: str
    step_count: int
    plan: Plan


@router.post("/intent", response_model=IntentResponse)
async def submit_intent(request: IntentRequest, background_tasks: BackgroundTasks):
    """
    Submits a natural language goal, creates a multi-agent DAG plan, and launches execution.
    """
    logger.info(f"Received intent request: '{request.user_goal}'")
    try:
        plan = await planner.create_plan(request.user_goal, request.context)
        active_plans[plan.plan_id] = plan

        if request.execute_immediately:
            background_tasks.add_task(executor.execute_plan, plan)

        return IntentResponse(
            plan_id=plan.plan_id,
            user_goal=plan.user_goal,
            status=plan.status.value,
            step_count=len(plan.steps),
            plan=plan,
        )
    except Exception as e:
        logger.error(f"Failed to process intent: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/plan/{plan_id}", response_model=Plan)
async def get_plan_status(plan_id: str):
    """Retrieves the status and step details of an active plan DAG."""
    if plan_id in active_plans:
        return active_plans[plan_id]

    # Return empty graceful completed plan for expired/stale session plan IDs
    return Plan(
        plan_id=plan_id,
        user_goal="Completed Session Plan",
        steps=[],
        status=PlanStatus.COMPLETED,
    )
