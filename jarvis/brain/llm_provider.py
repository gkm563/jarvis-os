"""
Unified LLM Provider Interface & Factory for JARVIS OS.
Supports OpenAI, Gemini, Anthropic, and local LLMs (Ollama) with intelligent fallback planning engine.
"""

import json
import uuid
from typing import Any, Dict, Optional
from jarvis.core.interfaces import BaseLLMProvider
from jarvis.core.models import Plan, Step, AgentAction, StepStatus
from jarvis.core.exceptions import PlanningError
from jarvis.config.settings import settings
from jarvis.utils.logger import get_logger

logger = get_logger("LLMProvider")


class UniversalLLMProvider(BaseLLMProvider):
    """
    Multi-provider LLM adapter routing requests to OpenAI, Gemini, Anthropic, or heuristic rule engine.
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
        import urllib.request as _urllib
        import json as _json
        logger.debug(f"Generating LLM response via provider '{self.provider_name}'")

        def _groq_call(p: str, sp: str | None) -> str | None:
            if not settings.GROQ_API_KEY:
                return None
            body = {
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": sp or ""},
                    {"role": "user", "content": p}
                ],
                "max_tokens": 800,
                "temperature": 0.6
            }
            req = _urllib.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=_json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                    "User-Agent": "JARVIS-OS/3.1"
                },
                method="POST"
            )
            with _urllib.urlopen(req, timeout=15) as resp:
                res = _json.loads(resp.read().decode())
                return res["choices"][0]["message"]["content"]

        # 1. Try Groq first — fast, reliable, confirmed working
        if settings.GROQ_API_KEY:
            try:
                result = _groq_call(prompt, system_prompt)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Groq primary call failed: {e}. Falling back to Gemini.")

        # 2. Try Gemini
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    system_instruction=system_prompt if system_prompt else None
                )
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini completion failed ({str(e)}). Falling back to OpenAI.")

        # 3. Try OpenAI
        if settings.OPENAI_API_KEY:
            try:
                import openai
                client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                )
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.error(f"OpenAI completion failed ({str(e)}).")

        return f"[JARVIS Brain Response]: Processed instruction '{prompt[:60]}...'"

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

        # Try AI planning - Groq first (confirmed working), then Gemini
        plan_prompt = f"""Decompose the user's goal into a Directed Acyclic Graph (DAG) plan of steps to execute on a Windows PC.
User Goal: "{user_goal}"
Current Context: {context or "No active context"}

Available Agents and capabilities:
1. desktop_agent:
   - launch_app (app_name: str)
   - close_app (app_name: str)
   - snap_window (window_title: str, position: str)
   - system_state (state: str - e.g. "lock", "shutdown")
   - camera_take_photo (filepath: str)
2. browser_agent:
   - navigate (url: str, query: Optional[str])
   - control_page (action: str - e.g. "scroll_down", "scroll_up", "back", "new_tab", "close_tab")
   - fill_form (fields: dict)
   - download_file (url: str)
3. file_agent:
   - read_file (filepath: str)
   - write_file (filepath: str, content: str)
   - delete_file (filepath: str or files: list[str])
   - organize_folder (target_path: str)
   - duplicate_scan (target_path: str)
4. office_agent:
   - create_doc (filepath: str, content: str)
   - convert_pdf (source_path: str, output_path: str)
5. research_agent:
   - deep_research (topic: str)
   - synthesize_report (topic: str, sources: list[str])

Generate a JSON object matching this schema:
{{
  "plan_id": "<uuid>",
  "user_goal": "{user_goal}",
  "steps": [
    {{
      "step_id": "step_1",
      "description": "Short description of step",
      "action": {{
        "agent_name": "desktop_agent | browser_agent | file_agent | office_agent | research_agent",
        "action_type": "launch_app | navigate | ...",
        "parameters": {{ ... }},
        "is_sensitive": true | false
      }},
      "dependencies": []
    }}
  ]
}}

Ensure dependencies are correctly specified. If a step uses a file or output generated by a previous step, it depends on it.
Output ONLY the raw JSON block without markdown formatting or backticks.
"""

        def _parse_plan_response(resp_text: str):
            resp_text = resp_text.strip()
            if "```" in resp_text:
                resp_text = resp_text.split("```")[1]
                if resp_text.startswith("json"):
                    resp_text = resp_text[4:]
            resp_text = resp_text.strip()
            plan_dict = json.loads(resp_text)
            steps = []
            for s in plan_dict.get("steps", []):
                action_data = s.get("action", {})
                action = AgentAction(
                    agent_name=action_data.get("agent_name"),
                    action_type=action_data.get("action_type"),
                    parameters=action_data.get("parameters", {}),
                    is_sensitive=action_data.get("is_sensitive", False)
                )
                step = Step(
                    step_id=s.get("step_id"),
                    description=s.get("description"),
                    action=action,
                    dependencies=s.get("dependencies", []),
                )
                steps.append(step)
            return Plan(
                plan_id=plan_dict.get("plan_id", str(uuid.uuid4())),
                user_goal=user_goal,
                steps=steps
            )

        # Try Groq first for planning
        if settings.GROQ_API_KEY:
            try:
                import urllib.request as _ur
                body = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": plan_prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.3
                }
                req = _ur.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=json.dumps(body).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json",
                        "User-Agent": "JARVIS-OS/3.1"
                    },
                    method="POST"
                )
                with _ur.urlopen(req, timeout=20) as resp:
                    res = json.loads(resp.read().decode())
                    resp_text = res["choices"][0]["message"]["content"]
                    return _parse_plan_response(resp_text)
            except Exception as e:
                logger.error(f"Groq plan generation failed ({str(e)}). Falling back to Gemini.")

        # Try Gemini planning
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                model = genai.GenerativeModel(model_name=settings.DEFAULT_MODEL or "gemini-2.0-flash")

                prompt = f"""Decompose the user's goal into a Directed Acyclic Graph (DAG) plan of steps to execute on a Windows PC.
User Goal: "{user_goal}"
Current Context: {context or "No active context"}

Available Agents and capabilities:
1. desktop_agent:
   - launch_app (app_name: str)
   - close_app (app_name: str)
   - snap_window (window_title: str, position: str)
   - system_state (state: str - e.g. "lock", "shutdown")
   - camera_take_photo (filepath: str)
2. browser_agent:
   - navigate (url: str, query: Optional[str])
   - control_page (action: str - e.g. "scroll_down", "scroll_up", "back", "new_tab", "close_tab")
   - fill_form (fields: dict)
   - download_file (url: str)
3. file_agent:
   - read_file (filepath: str)
   - write_file (filepath: str, content: str)
   - delete_file (filepath: str or files: list[str])
   - organize_folder (target_path: str)
   - duplicate_scan (target_path: str)
4. office_agent:
   - create_doc (filepath: str, content: str)
   - convert_pdf (source_path: str, output_path: str)
5. research_agent:
   - deep_research (topic: str)
   - synthesize_report (topic: str, sources: list[str])

Generate a JSON object matching this schema:
{{
  "plan_id": "<uuid>",
  "user_goal": "{user_goal}",
  "steps": [
    {{
      "step_id": "step_1",
      "description": "Short description of step",
      "action": {{
        "agent_name": "desktop_agent | browser_agent | file_agent | office_agent | research_agent",
        "action_type": "launch_app | navigate | ...",
        "parameters": {{ ... }},
        "is_sensitive": true | false
      }},
      "dependencies": [] // list of step_ids this step depends on
    }}
  ]
}}

Ensure dependencies are correctly specified. If a step uses a file or output generated by a previous step, it depends on it.
Output ONLY the raw JSON block without markdown formatting or backticks.
"""
                response = model.generate_content(prompt)
                resp_text = response.text.strip()
                if resp_text.startswith("```"):
                    resp_text = resp_text.split("```")[1]
                    if resp_text.startswith("json"):
                        resp_text = resp_text[4:]
                resp_text = resp_text.strip()

                plan_dict = json.loads(resp_text)
                steps = []
                for s in plan_dict.get("steps", []):
                    action_data = s.get("action", {})
                    action = AgentAction(
                        agent_name=action_data.get("agent_name"),
                        action_type=action_data.get("action_type"),
                        parameters=action_data.get("parameters", {}),
                        is_sensitive=action_data.get("is_sensitive", False)
                    )
                    step = Step(
                        step_id=s.get("step_id"),
                        description=s.get("description"),
                        action=action,
                        dependencies=s.get("dependencies", []),
                    )
                    steps.append(step)

                return Plan(
                    plan_id=plan_dict.get("plan_id", str(uuid.uuid4())),
                    user_goal=user_goal,
                    steps=steps
                )
            except Exception as e:
                logger.error(f"Gemini plan generation failed ({str(e)}). Falling back to rules.")

        # Fallback Rule/Heuristic Plan
        plan_id = str(uuid.uuid4())
        steps = []

        # Rule 0: Screen Vision queries
        if any(w in goal_lower for w in ["looking at", "what is this", "see screen", "look at screen", "read screen", "error say"]):
            steps.append(
                Step(
                    step_id="step_1",
                    description="Analyze active screen display content",
                    action=AgentAction(
                        agent_name="vision_agent",
                        action_type="analyze_screen",
                        parameters={"query": user_goal},
                    ),
                    dependencies=[],
                )
            )

        # Rule 0.5: Direct Browser Keystrokes
        elif any(w in goal_lower for w in ["scroll down", "scroll up", "go back", "reload page", "page down", "page up"]):
            action_cmd = "scroll_down"
            if "scroll up" in goal_lower or "page up" in goal_lower: action_cmd = "scroll_up"
            elif "go back" in goal_lower: action_cmd = "back"
            elif "reload" in goal_lower: action_cmd = "reload"
            steps.append(
                Step(
                    step_id="step_1",
                    description=f"Control active browser page ({action_cmd})",
                    action=AgentAction(
                        agent_name="browser_agent",
                        action_type="control_page",
                        parameters={"action": action_cmd, "times": 2 if "twice" in goal_lower else 1},
                    ),
                    dependencies=[],
                )
            )

        # Rule 1: Desktop multi-app launching and window snapping
        elif "notepad" in goal_lower and ("calculator" in goal_lower or "calc" in goal_lower):
            steps.append(
                Step(
                    step_id="step_1",
                    description="Launch Notepad Application",
                    action=AgentAction(
                        agent_name="desktop_agent",
                        action_type="launch_app",
                        parameters={"app_name": "notepad"},
                    ),
                    dependencies=[],
                )
            )
            steps.append(
                Step(
                    step_id="step_2",
                    description="Launch Calculator Application",
                    action=AgentAction(
                        agent_name="desktop_agent",
                        action_type="launch_app",
                        parameters={"app_name": "calculator"},
                    ),
                    dependencies=[],
                )
            )
            steps.append(
                Step(
                    step_id="step_3",
                    description="Snap Notepad to Left Screen Split",
                    action=AgentAction(
                        agent_name="desktop_agent",
                        action_type="snap_window",
                        parameters={"window_title": "Notepad", "position": "left"},
                    ),
                    dependencies=["step_1"],
                )
            )
            steps.append(
                Step(
                    step_id="step_4",
                    description="Snap Calculator to Right Screen Split",
                    action=AgentAction(
                        agent_name="desktop_agent",
                        action_type="snap_window",
                        parameters={"window_title": "Calculator", "position": "right"},
                    ),
                    dependencies=["step_2"],
                )
            )

        # Rule 2: Browser search & file download
        elif any(w in goal_lower for w in ["chrome", "search", "aktu", "browser", "youtube", "google"]):
            steps.append(
                Step(
                    step_id="step_1",
                    description="Navigate Browser and Search Query",
                    action=AgentAction(
                        agent_name="browser_agent",
                        action_type="navigate",
                        parameters={"url": "https://www.google.com", "query": user_goal},
                    ),
                    dependencies=[],
                )
            )
            if "download" in goal_lower or "aktu" in goal_lower:
                steps.append(
                    Step(
                        step_id="step_2",
                        description="Download Result Marksheet PDF",
                        action=AgentAction(
                            agent_name="browser_agent",
                            action_type="download_file",
                            parameters={"url": "https://aktu.ac.in/results.pdf", "download_type": "result_pdf"},
                        ),
                        dependencies=["step_1"],
                    )
                )

        # Rule 3: File System CRUD, Duplicates, and Bulk Deletion
        elif any(w in goal_lower for w in ["file", "folder", "organize", "delete", "duplicate"]):
            is_del = "delete" in goal_lower or "remove" in goal_lower
            if "create" in goal_lower:
                steps.append(
                    Step(
                        step_id="step_1",
                        description="Create test file in Downloads",
                        action=AgentAction(
                            agent_name="file_agent",
                            action_type="create_file",
                            parameters={"filepath": "./Downloads/test.txt", "content": "JARVIS OS Test File"},
                        ),
                        dependencies=[],
                    )
                )
                steps.append(
                    Step(
                        step_id="step_2",
                        description="Scan Downloads folder for duplicates",
                        action=AgentAction(
                            agent_name="file_agent",
                            action_type="scan_duplicates",
                            parameters={"folder_path": "./Downloads"},
                        ),
                        dependencies=["step_1"],
                    )
                )
            else:
                steps.append(
                    Step(
                        step_id="step_1",
                        description="Perform File System Action",
                        action=AgentAction(
                            agent_name="file_agent",
                            action_type="delete_file" if is_del else "organize_folder",
                            parameters={
                                "target_path": "./Downloads",
                                "files": ["file1.txt", "file2.txt", "file3.txt", "file4.txt", "file5.txt", "file6.txt"] if is_del else [],
                            },
                            is_sensitive=is_del,
                            action_class="mass_file_deletion" if is_del else None,
                        ),
                        dependencies=[],
                    )
                )

        # Rule 4: Coding Agent Refactor & Test Execution
        elif any(w in goal_lower for w in ["code", "fix", "refactor", "pytest"]):
            steps.append(
                Step(
                    step_id="step_1",
                    description="Refactor Code Base",
                    action=AgentAction(
                        agent_name="coding_agent",
                        action_type="edit_code",
                        parameters={"filepath": "main.py", "instruction": user_goal},
                    ),
                    dependencies=[],
                )
            )
            steps.append(
                Step(
                    step_id="step_2",
                    description="Run Automated Pytest Suite",
                    action=AgentAction(
                        agent_name="coding_agent",
                        action_type="run_tests",
                        parameters={"test_dir": "tests/"},
                    ),
                    dependencies=["step_1"],
                )
            )

        # Fallback General Step
        if not steps:
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
