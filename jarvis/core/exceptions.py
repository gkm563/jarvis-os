"""
Domain Exceptions Hierarchy for JARVIS OS.
Follows Clean Architecture guidelines for granular, readable error propagation.
"""


class JarvisError(Exception):
    """Base exception class for all errors generated within JARVIS OS."""

    def __init__(self, message: str, code: str = "JARVIS_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class SecurityError(JarvisError):
    """Raised when a security policy or permission validation fails."""

    def __init__(self, message: str):
        super().__init__(message, code="SECURITY_ERROR")


class VaultError(SecurityError):
    """Raised when encryption, key derivation, or credential retrieval fails."""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "VAULT_ERROR"


class ActionDeniedError(SecurityError):
    """Raised when an agent action is denied due to missing human confirmation or permissions."""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = "ACTION_DENIED"


class AgentError(JarvisError):
    """Base exception for agent execution errors."""

    def __init__(self, agent_name: str, message: str):
        super().__init__(f"Agent [{agent_name}] failed: {message}", code="AGENT_ERROR")
        self.agent_name = agent_name


class PlanningError(JarvisError):
    """Raised when natural language intent cannot be parsed or decomposed into a valid DAG plan."""

    def __init__(self, message: str):
        super().__init__(message, code="PLANNING_ERROR")


class ExecutionError(JarvisError):
    """Raised when a task DAG execution fails or rolls back."""

    def __init__(self, step_id: str, message: str):
        super().__init__(f"Execution failed at step {step_id}: {message}", code="EXECUTION_ERROR")
        self.step_id = step_id


class VisionError(AgentError):
    """Raised when vision or semantic UI element detection fails."""

    def __init__(self, message: str):
        super().__init__("VisionAgent", message)


class StorageError(JarvisError):
    """Raised when SQLite or Vector DB operations fail."""

    def __init__(self, message: str):
        super().__init__(message, code="STORAGE_ERROR")
