"""
FastAPI Endpoints for Agent Direct Invocation & Capability Inspection.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any
from jarvis.orchestration.executor import agent_registry
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("API_Agents")
router = APIRouter(prefix="/v1", tags=["Agents"])


@router.get("/agents")
async def list_agents() -> List[Dict[str, Any]]:
    """Lists all registered domain agents and their capabilities."""
    agents = []
    for name, agent in agent_registry._agents.items():
        agents.append({
            "name": agent.name,
            "description": agent.description,
            "capabilities": agent.capabilities,
        })
    return agents


@router.post("/agents/{agent_name}/action", response_model=ExecutionResult)
async def invoke_agent_action(agent_name: str, action: AgentAction):
    """Direct low-level invocation of a specific domain agent."""
    agent = agent_registry.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")

    logger.info(f"Direct API call to agent '{agent_name}' action '{action.action_type}'")
    return await agent.execute(action)
