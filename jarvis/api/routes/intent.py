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

    # Update visual status to thinking
    await ws_manager.broadcast({"type": "status", "state": "thinking"})

    llm = UniversalLLMProvider()

    # Classify: question or automation
    classification_prompt = f"""Classify the user prompt into one of these two categories:
- "knowledge": asking a question, wanting an explanation, wanting information, wanting advice, greeting, or having a conversation (e.g. "who is CEO of Microsoft", "explain recursion", "hello", "what is 2+2", "tell me a joke", "what is AI")
- "automation": wants to DO something on the computer (e.g. "open chrome", "create a file", "take screenshot", "close notepad", "send message")

User Prompt: "{goal}"
Output ONLY one word: knowledge OR automation"""

    category = "knowledge"
    try:
        category = (await llm.generate_response(classification_prompt)).lower().strip().strip('"\'')
        logger.info(f"Classified as: '{category}'")
    except Exception as e:
        logger.error(f"Classification failed: {e}")

    if "automation" in category:
        # --- AUTOMATION PATH ---
        try:
            plan = await planner.create_plan(goal)
            active_plans[plan.plan_id] = plan
        except Exception as e:
            logger.error(f"Plan creation failed: {e}")
            err_msg = f"Sorry, I couldn't figure out how to do that: {e}"
            await ws_manager.broadcast({"type": "message", "author": "JARVIS", "text": err_msg})
            await ws_manager.broadcast({"type": "status", "state": "speaking"})
            speak(err_msg, block=False)
            await ws_manager.broadcast({"type": "status", "state": "idle"})
            return

        # Execute steps, collect results
        completed_steps = []
        for step in plan.steps:
            await ws_manager.broadcast({"type": "status", "state": "thinking"})
            result = await executor._execute_step(step)

            if not result.success:
                fail_msg = f"Couldn't complete that — {result.error_message}"
                await ws_manager.broadcast({"type": "message", "author": "JARVIS", "text": fail_msg})
                await ws_manager.broadcast({"type": "status", "state": "speaking"})
                speak(fail_msg, block=True)
                await ws_manager.broadcast({"type": "status", "state": "idle"})
                return
            completed_steps.append(step.description)

        # Ask LLM to summarize what was done in a natural, brief sentence
        steps_summary = "; ".join(completed_steps) if completed_steps else goal
        summary_prompt = f"""The user asked: "{goal}"
I executed these steps: {steps_summary}
Write ONE short, natural confirmation sentence telling the user what was done. Be direct and friendly. No filler, no bullet points."""
        try:
            done_msg = await llm.generate_response(summary_prompt)
            done_msg = done_msg.strip()
        except Exception:
            done_msg = "Done."

        await ws_manager.broadcast({"type": "message", "author": "JARVIS", "text": done_msg})
        await ws_manager.broadcast({"type": "status", "state": "speaking"})
        speak(done_msg, block=True)
        await ws_manager.broadcast({"type": "status", "state": "idle"})

    else:
        # --- KNOWLEDGE / CONVERSATION PATH ---
        try:
            system_prompt = """You are JARVIS — a sharp, witty, and knowledgeable personal AI assistant running on a Windows PC.

RULES:
- Answer the question fully and correctly.
- Be concise: 1–4 sentences for simple questions, a bit more if it's complex.
- Speak naturally — the user hears this out loud, so avoid markdown, bullet points, or headers.
- Be friendly and direct. No filler phrases like "Great question!" or "Certainly!".
- If greeted, greet back warmly in one line.
- If asked to tell a joke or be creative, do it confidently."""
            response = await llm.generate_response(goal, system_prompt=system_prompt)
            response = response.strip()
        except Exception as e:
            logger.error(f"LLM response failed: {e}")
            response = "I ran into a problem answering that. Try again?"

        await ws_manager.broadcast({"type": "message", "author": "JARVIS", "text": response})
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
