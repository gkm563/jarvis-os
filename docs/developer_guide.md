# JARVIS OS - Developer & Plugin Guide

## Getting Started

### Quickstart Setup
```bash
# Clone the repository
git clone https://github.com/jarvis-os/jarvis-os.git
cd jarvis-os

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Run unit and integration tests
python -m pytest tests/ -v

# Launch the FastAPI microservice
python -m jarvis.main
```

---

## Developing a New Agent

To extend JARVIS OS with a custom domain agent:

1. Create a new module in `jarvis/agents/my_custom_agent.py`.
2. Inherit from `AbstractAgent` (`jarvis.agents.base.AbstractAgent`).
3. Implement `name`, `description`, `capabilities`, and `execute(action: AgentAction)`.
4. Register your agent in `jarvis/agents/__init__.py`.

```python
from jarvis.agents.base import AbstractAgent
from jarvis.core.models import AgentAction, ExecutionResult

class CustomAgent(AbstractAgent):
    @property
    def name(self) -> str:
        return "custom_agent"

    @property
    def description(self) -> str:
        return "Custom domain automation agent."

    @property
    def capabilities(self) -> list[str]:
        return ["custom_action"]

    async def execute(self, action: AgentAction) -> ExecutionResult:
        return ExecutionResult(success=True, data={"result": "custom output"})
```

---

## Developing a Plugin

Third-party tools integrate via the Plugin SDK (`jarvis.plugins.sdk.BasePlugin`):

```python
from jarvis.plugins.sdk import BasePlugin, PluginManifest

class SlackPlugin(BasePlugin):
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            plugin_id="com.slack.plugin",
            name="Slack Plugin",
            version="1.0.0",
            author="Dev Team",
            required_permissions=["network"],
            entry_point="slack_plugin.py",
        )

    async def execute_plugin_action(self, action_type: str, parameters: dict) -> dict:
        return {"status": "message_sent"}
```
