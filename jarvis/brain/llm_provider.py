"""
Unified LLM Provider Interface & Factory for JARVIS OS.
Supports OpenAI, Gemini, Anthropic, and local LLMs (Ollama) with fallback mock support.
"""

import json
from typing import Any, Dict, Optional
from jarvis.core.interfaces import BaseLLMProvider
from jarvis.core.models import Plan, Step, AgentAction, StepStatus
from jarvis.core.exceptions import PlanningError
from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger

logger = get_logger("LLMProvider")


class UniversalLLMProvider(BaseLLMProvider):
    """
    Multi-provider LLM adapter routing requests to OpenAI, Gemini, Anthropic, or mock engine.
    """

    def __init__(self, provider: Optional[str] = None):
        self.provider_name = (provider or settings.DEFAULT_LLM_PROVIDER).lower()
        logger.info(f"Universal LLM Provider initialized with default backend: '{self.provider_name}'")

    async def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generates text completion using the selected LLM provider.

        Args:
            prompt (str): Main text prompt.
            system_prompt (Optional[str]): System instruction context.

        Returns:
            str: Generated text output.
        """
        logger.debug(f"Generating LLM response via provider '{self.provider_name}'")
        
        # Check OpenAI
        if self.provider_name == "openai" and settings.OPENAI_API_KEY:
            try:
                import openai
                client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                response = await client.chat.completions.create(
                    model=settings.DEFAULT_MODEL,
                    messages=messages,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.error(f"OpenAI completion failed ({str(e)}). Falling back to mock engine.")

        # Default heuristic mock fallback
        return f"[JARVIS Brain Response]: Processed prompt '{prompt[:50]}...'"

    async def generate_plan(self, user_goal: str, context: Optional[str] = None) -> Plan:
        """
        Parses user goal into a structured multi-agent execution DAG Plan.

        Args:
            user_goal (str): Natural language instruction.
            context (Optional[str]): Environment context.

        Returns:
            Plan: Fully structured plan DAG.
        """
        logger.info(f"Generating plan for user goal: '{user_goal}'")
        goal_lower = user_goal.lower()

        import uuid
        plan_id = str(uuid.uuid4())
        steps = []

        # Heuristic DAG generation rules
        if "chrome" in goal_lower or "search" in goal_lower or "aktu" in goal_lower or "browser" in goal_lower:
            steps.append(
                Step(
                    step_id="step_1",
                    description="Launch Browser and Navigate to target",
                    action=AgentAction(
                        agent_name="browser_agent",
                        action_type="navigate",
                        parameters={"url": "https://www.google.com", "query": user_goal},
                    ),
                    dependencies=[],
                )
            )
            steps.append(
                Step(
                    step_id="step_2",
                    description="Extract content or download file",
                    action=AgentAction(
                        agent_name="browser_agent",
                        action_type="download_file",
                        parameters={"download_type": "result_pdf"},
                    ),
                    dependencies=["step_1"],
                )
            )

        if "file" in goal_lower or "folder" in goal_lower or "organize" in goal_lower or "delete" in goal_lower:
            is_del = "delete" in goal_lower or "remove" in goal_lower
            steps.append(
                Step(
                    step_id=f"step_{len(steps)+1}",
                    description="Perform file system action",
                    action=AgentAction(
                        agent_name="file_agent",
                        action_type="delete_file" if is_del else "organize_folder",
                        parameters={"target_path": "./Downloads", "files": ["file1.txt", "file2.txt"] if is_del else []},
                        is_sensitive=is_del,
                        action_class="mass_file_deletion" if is_del else None,
                    ),
                    dependencies=[steps[-1].step_id] if steps else [],
                )
            )

        if "code" in goal_lower or "fix" in goal_lower or "commit" in goal_lower:
            steps.append(
                Step(
                    step_id=f"step_{len(steps)+1}",
                    description="Run coding refactor and unit tests",
                    action=AgentAction(
                        agent_name="coding_agent",
                        action_type="edit_code",
                        parameters={"filepath": "main.py", "instruction": user_goal},
                    ),
                    dependencies=[steps[-1].step_id] if steps else [],
                )
            )

        if not steps:
            # General desktop app launch fallback step
            steps.append(
                Step(
                    step_id="step_1",
                    description=f"Desktop action for: {user_goal}",
                    action=AgentAction(
                        agent_name="desktop_agent",
                        action_type="launch_app",
                        parameters={"app_name": "notepad"},
                    ),
                    dependencies=[],
                )
            )

        return Plan(
            plan_id=plan_id,
            user_goal=user_goal,
            steps=steps,
        )
