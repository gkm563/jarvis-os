"""
Phase 2-4 Agent Stubs for JARVIS OS.
Provides typed stub implementations for additional domain agents specified in the PRD.
"""

from typing import List
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult
from jarvis.utils.logger import get_logger

logger = get_logger("AgentStubs")


class WhatsAppAgent(AbstractAgent):
    @property
    def name(self) -> str: return "whatsapp_agent"
    @property
    def description(self) -> str: return "Sends/receives WhatsApp Web messages and scheduled notifications."
    @property
    def capabilities(self) -> List[str]: return ["send_message", "read_chat"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        logger.info(f"WhatsAppAgent executing action '{action.action_type}'")
        return ExecutionResult(success=True, data={"status": "executed", "agent": self.name})


class TelegramAgent(AbstractAgent):
    @property
    def name(self) -> str: return "telegram_agent"
    @property
    def description(self) -> str: return "Manages Telegram messages, channels, media uploads, and bot routines."
    @property
    def capabilities(self) -> List[str]: return ["send_message", "manage_bot"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        logger.info(f"TelegramAgent executing action '{action.action_type}'")
        return ExecutionResult(success=True, data={"status": "executed", "agent": self.name})


class SecuritySystemAgent(AbstractAgent):
    @property
    def name(self) -> str: return "security_agent"
    @property
    def description(self) -> str: return "Central security agent interface for vault secrets, anomaly reporting, and permissions."
    @property
    def capabilities(self) -> List[str]: return ["vault_access", "permission_check"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        logger.info(f"SecuritySystemAgent executing action '{action.action_type}'")
        return ExecutionResult(success=True, data={"status": "executed", "agent": self.name})
