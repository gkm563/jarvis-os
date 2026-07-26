"""
Domain Entity Models for JARVIS OS.
Defines data structures for Tasks, Plans, DAG Steps, Actions, Results, and User Profiles.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ROLLED_BACK = "rolled_back"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentAction(BaseModel):
    """Encapsulates a single action dispatched to a domain agent."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent_name: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    is_sensitive: bool = False
    action_class: Optional[str] = None


class ExecutionResult(BaseModel):
    """Result returned by an agent after executing an action."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    screenshot_path: Optional[str] = None


class Step(BaseModel):
    """A discrete unit of work in an execution DAG."""
    step_id: str
    description: str
    action: AgentAction
    dependencies: List[str] = Field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[ExecutionResult] = None
    retry_count: int = 0
    max_retries: int = 3
    rollback_action: Optional[AgentAction] = None


class Plan(BaseModel):
    """A Directed Acyclic Graph (DAG) plan of steps resolving a user task."""
    plan_id: str
    user_goal: str
    steps: List[Step] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_cost_usd: float = 0.0


class UserProfile(BaseModel):
    """User preferences, contacts, and configuration data."""
    user_id: str
    name: str
    default_browser: str = "chrome"
    locale: str = "en_US"
    favorite_apps: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)


class PermissionScope(str, Enum):
    DESKTOP = "desktop"
    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    CODING = "coding"
    VISION = "vision"
    VOICE = "voice"
    EMAIL = "email"
    SYSTEM = "system"


class AuditLogRecord(BaseModel):
    """Audit log entry capturing system actions for transparency and compliance."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: str
    agent_name: str
    action_type: str
    parameters: Dict[str, Any]
    status: str
    execution_time_ms: float
    user_confirmed: bool = False
