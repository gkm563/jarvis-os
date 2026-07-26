"""
AI Coding Agent (FR-3) for JARVIS OS.
Pair-programmer agent handling code generation, refactoring, testing, and Git/GitHub automation.
"""

import ast
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("CodingAgent")


class AICodingAgent(AbstractAgent):
    """
    AI Coding Agent providing pair-programming capabilities and local Git workflow automation.
    """

    @property
    def name(self) -> str:
        return "coding_agent"

    @property
    def description(self) -> str:
        return "Generates, explains, refactors, tests code across languages and automates Git/GitHub commands."

    @property
    def capabilities(self) -> List[str]:
        return ["read_code", "edit_code", "run_test", "git_commit", "git_push"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        """Executes AI coding action."""
        if not await self.validate_action(action):
            return ExecutionResult(success=False, error_message=f"Unsupported action: {action.action_type}")

        action_type = action.action_type
        params = action.parameters

        try:
            if action_type == "read_code":
                filepath = params.get("filepath", "")
                return await self._read_code(filepath)

            elif action_type == "edit_code":
                filepath = params.get("filepath", "")
                instruction = params.get("instruction", "")
                content = params.get("content")
                return await self._edit_code(filepath, instruction, content)

            elif action_type == "run_test":
                command = params.get("command", "pytest")
                return await self._run_tests(command)

            elif action_type == "git_commit":
                message = params.get("message", "Auto commit by JARVIS Coding Agent")
                return await self._git_commit(message)

            elif action_type == "git_push":
                remote = params.get("remote", "origin")
                branch = params.get("branch", "main")
                return await self._git_push(remote, branch)

            return ExecutionResult(success=False, error_message=f"Unhandled action type '{action_type}'")

        except Exception as e:
            logger.error(f"Coding Agent action '{action_type}' failed: {str(e)}")
            return ExecutionResult(success=False, error_message=str(e))

    async def _read_code(self, filepath: str) -> ExecutionResult:
        """Reads code and validates Python syntax via AST parser."""
        p = Path(filepath)
        if not p.exists():
            return ExecutionResult(success=False, error_message=f"File not found: {filepath}")

        code = p.read_text(encoding="utf-8")
        is_valid_python = True
        ast_error = None

        if p.suffix == ".py":
            try:
                ast.parse(code)
            except SyntaxError as se:
                is_valid_python = False
                ast_error = str(se)

        return ExecutionResult(
            success=True,
            data={
                "filepath": filepath,
                "code": code,
                "is_valid_python": is_valid_python,
                "ast_error": ast_error,
            },
        )

    async def _edit_code(self, filepath: str, instruction: str, content: str = None) -> ExecutionResult:
        """Edits or generates code for a file with instruction context."""
        p = Path(filepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        new_content = content or f"# Refactored per instruction: {instruction}\n"
        p.write_text(new_content, encoding="utf-8")
        logger.info(f"Code edited for '{filepath}' per instruction '{instruction}'")
        return ExecutionResult(success=True, data={"filepath": filepath, "instruction": instruction})

    async def _run_tests(self, command: str) -> ExecutionResult:
        """Runs project unit test suite."""
        logger.info(f"Running test suite: '{command}'")
        try:
            res = subprocess.run(command, shell=True, capture_output=True, text=True)
            passed = res.returncode == 0
            return ExecutionResult(
                success=passed,
                data={"command": command, "stdout": res.stdout, "stderr": res.stderr, "returncode": res.returncode},
            )
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Test runner failed: {str(e)}")

    async def _git_commit(self, message: str) -> ExecutionResult:
        """Stages changes and commits to local Git repository."""
        logger.info(f"Executing Git commit: '{message}'")
        try:
            subprocess.run("git add .", shell=True, check=True)
            subprocess.run(f'git commit -m "{message}"', shell=True, check=True)
            return ExecutionResult(success=True, data={"status": "committed", "message": message})
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Git commit failed: {str(e)}")

    async def _git_push(self, remote: str, branch: str) -> ExecutionResult:
        """Pushes local commits to remote Git repository."""
        logger.info(f"Executing Git push to '{remote}/{branch}'")
        try:
            subprocess.run(f"git push {remote} {branch}", shell=True, check=True)
            return ExecutionResult(success=True, data={"remote": remote, "branch": branch, "status": "pushed"})
        except Exception as e:
            return ExecutionResult(success=False, error_message=f"Git push failed: {str(e)}")
