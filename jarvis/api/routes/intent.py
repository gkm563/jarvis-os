"""
FastAPI Endpoint for Natural Language Intent Processing and Plan Retrieval.
"""

import asyncio
import uuid
import re
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from jarvis.brain.planner import TaskPlanner
from jarvis.orchestration.executor import ExecutionManager
from jarvis.core.models import Plan, PlanStatus, StepStatus, AgentAction, Step
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


async def process_user_command(goal: str):
    """Unified voice/text command planner and execution pipeline."""
    from voice_engine import speak
    from jarvis.brain.llm_provider import UniversalLLMProvider
    from jarvis.api.websocket import ws_manager
    from jarvis.config.settings import settings
    
    logger.info(f"Processing command intent: '{goal}'")
    
    # 1. Broadcast user's message to UI
    await ws_manager.broadcast({
        "type": "message",
        "author": "You",
        "text": goal,
        "is_user": True
    })
    
    # 2. Update visual status indicator to thinking
    await ws_manager.broadcast({"type": "status", "state": "thinking"})
    
    llm = UniversalLLMProvider()
    
    # 3. Classify if it's a general question or local system automation
    classification_prompt = f"""Classify the user prompt into one of these categories:
- "knowledge": The user is asking a general information question, educational topic, history, explanation, coding question (e.g. "who is CEO of Microsoft", "explain Dijkstra", "how World War happened", "what is this code", "hello", "hi").
- "automation": The user wants to perform action(s) on the computer (e.g. "open chrome", "create a file", "take a photo", "close notepad", "save work", "send whatsapp").

User Prompt: "{goal}"
Output ONLY the category name ("knowledge" or "automation")."""

    category = "knowledge"
    try:
        category = await llm.generate_response(classification_prompt)
        category = category.lower().strip().replace('"', '').replace("'", "")
        logger.info(f"Classified command category as: '{category}'")
    except Exception as e:
        logger.error(f"Classification failed: {e}. Defaulting to knowledge.")
        
    if "automation" in category:
        try:
            plan = await planner.create_plan(goal)
            active_plans[plan.plan_id] = plan
        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            err_msg = f"Something went wrong: {e}"
            await ws_manager.broadcast({"type": "message", "author": "JARVIS", "text": err_msg})
            await ws_manager.broadcast({"type": "status", "state": "idle"})
            speak(err_msg, block=False)
            return

        # Execute steps silently — no plan announcement, no step narration
        for step in plan.steps:
            await ws_manager.broadcast({"type": "status", "state": "thinking"})
            result = await executor._execute_step(step)

            if not result.success:
                fail_msg = f"Sorry, couldn't do that — {result.error_message}"
                await ws_manager.broadcast({"type": "message", "author": "JARVIS", "text": fail_msg})
                await ws_manager.broadcast({"type": "status", "state": "speaking"})
                speak(fail_msg, block=True)
                await ws_manager.broadcast({"type": "status", "state": "idle"})
                return

        success_msg = "Done, boss."
        await ws_manager.broadcast({"type": "message", "author": "JARVIS", "text": success_msg})
        await ws_manager.broadcast({"type": "status", "state": "speaking"})
        speak(success_msg, block=True)
        await ws_manager.broadcast({"type": "status", "state": "idle"})
        
    else:
        # Knowledge query
        try:
            system_prompt = """You are JARVIS — a personal AI assistant on a Windows PC.
BEHAVIOR:
- Answer questions directly in 1-3 short sentences.
- Keep replies short — the user hears this spoken aloud.
- Be friendly and professional."""
            response = await llm.generate_response(goal, system_prompt=system_prompt)
        except Exception as e:
            logger.error(f"LLM generate_response failed: {e}")
            response = f"I ran into an issue finding that answer: {e}"
            
        # Broadcast JARVIS reply bubble to UI
        await ws_manager.broadcast({
            "type": "message",
            "author": "JARVIS",
            "text": response
        })
        
        # Speak response aloud
        await ws_manager.broadcast({"type": "status", "state": "speaking"})
        speak(response, block=True)
        await ws_manager.broadcast({"type": "status", "state": "idle"})


@router.post("/intent", response_model=IntentResponse)
async def submit_intent(request: IntentRequest, background_tasks: BackgroundTasks):
    """
    Submits a natural language goal, creates a plan, and launches execution.
    """
    logger.info(f"Received intent request: '{request.user_goal}'")
    try:
        plan = await planner.create_plan(request.user_goal, request.context)
        active_plans[plan.plan_id] = plan

        if request.execute_immediately:
            background_tasks.add_task(process_user_command, request.user_goal)

        return IntentResponse(
            plan_id=plan.plan_id,
            user_goal=plan.user_goal,
            status="EXECUTING",
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

    return Plan(
        plan_id=plan_id,
        user_goal="Completed Session Plan",
        steps=[],
        status=PlanStatus.COMPLETED,
    )


@router.post("/trigger_mic")
async def trigger_mic(background_tasks: BackgroundTasks):
    """Triggers the local voice assistant mic listening and execution loop."""
    logger.info("Triggering local mic listening via Web UI request...")
    
    async def listen_and_run():
        from voice_engine import listen_best
        from jarvis.config.settings import settings
        from jarvis.api.websocket import ws_manager
        
        await ws_manager.broadcast({"type": "status", "state": "listening"})
        
        api_key = settings.GROQ_API_KEY
        text, err = listen_best(api_key, timeout_sec=10)
        
        if text:
            await process_user_command(text)
        else:
            await ws_manager.broadcast({"type": "status", "state": "idle"})
            if err and "Interrupted" not in err:
                await ws_manager.broadcast({
                    "type": "message",
                    "author": "JARVIS",
                    "text": f"Didn't hear you: {err}"
                })
                
    background_tasks.add_task(listen_and_run)
    return {"status": "triggered"}
