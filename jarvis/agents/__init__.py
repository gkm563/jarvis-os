"""
Agents Package Initialization.
Instantiates and registers all specialized domain agents into the Agent Registry.
"""

from jarvis.agents.desktop_agent import DesktopControlAgent
from jarvis.agents.file_agent import FileSystemAgent
from jarvis.agents.browser_agent import BrowserAutomationAgent
from jarvis.agents.coding_agent import AICodingAgent
from jarvis.agents.vision_agent import VisionAgent
from jarvis.agents.voice_agent import VoiceAssistantAgent
from jarvis.agents.email_agent import EmailAgent
from jarvis.agents.office_agent import OfficeAgent
from jarvis.agents.developer_agent import DeveloperAgent
from jarvis.agents.database_agent import DatabaseAgent
from jarvis.agents.scheduler_agent import SchedulerAgent
from jarvis.agents.research_agent import InternetResearchAgent
from jarvis.agents.stubs.stubs import (
    WhatsAppAgent,
    TelegramAgent,
    SecuritySystemAgent,
)
from jarvis.orchestration.executor import agent_registry

# Instantiate Domain Agents
desktop_agent = DesktopControlAgent()
file_agent = FileSystemAgent()
browser_agent = BrowserAutomationAgent()
coding_agent = AICodingAgent()
vision_agent = VisionAgent()
voice_agent = VoiceAssistantAgent()
email_agent = EmailAgent()
office_agent = OfficeAgent()
developer_agent = DeveloperAgent()
database_agent = DatabaseAgent()
scheduler_agent = SchedulerAgent()
research_agent = InternetResearchAgent()

# Instantiate Remaining Phase 2-4 Stubs
whatsapp_agent = WhatsAppAgent()
telegram_agent = TelegramAgent()
security_agent = SecuritySystemAgent()

# Register all agents into Central Agent Registry
for agent in [
    desktop_agent,
    file_agent,
    browser_agent,
    coding_agent,
    vision_agent,
    voice_agent,
    email_agent,
    office_agent,
    developer_agent,
    database_agent,
    scheduler_agent,
    research_agent,
    whatsapp_agent,
    telegram_agent,
    security_agent,
]:
    agent_registry.register(agent)

__all__ = [
    "desktop_agent",
    "file_agent",
    "browser_agent",
    "coding_agent",
    "vision_agent",
    "voice_agent",
    "email_agent",
    "office_agent",
    "developer_agent",
    "database_agent",
    "scheduler_agent",
    "research_agent",
    "whatsapp_agent",
    "telegram_agent",
    "security_agent",
]
