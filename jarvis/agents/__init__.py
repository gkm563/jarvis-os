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
from jarvis.agents.stubs.stubs import (
    EmailAgent,
    OfficeAgent,
    DeveloperAgent,
    DatabaseAgent,
    SchedulerAgent,
    WhatsAppAgent,
    TelegramAgent,
    InternetResearchAgent,
    SecuritySystemAgent,
)
from jarvis.orchestration.executor import agent_registry

# Instantiate Primary Phase-1 Agents
desktop_agent = DesktopControlAgent()
file_agent = FileSystemAgent()
browser_agent = BrowserAutomationAgent()
coding_agent = AICodingAgent()
vision_agent = VisionAgent()
voice_agent = VoiceAssistantAgent()

# Instantiate Phase 2-4 Agents
email_agent = EmailAgent()
office_agent = OfficeAgent()
developer_agent = DeveloperAgent()
database_agent = DatabaseAgent()
scheduler_agent = SchedulerAgent()
whatsapp_agent = WhatsAppAgent()
telegram_agent = TelegramAgent()
research_agent = InternetResearchAgent()
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
    whatsapp_agent,
    telegram_agent,
    research_agent,
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
    "whatsapp_agent",
    "telegram_agent",
    "research_agent",
    "security_agent",
]
