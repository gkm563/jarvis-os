"""
Security Package Initialization.
"""

from jarvis.security.vault import AESVault
from jarvis.security.permissions import PermissionManager
from jarvis.security.sensitive_gate import SensitiveActionGate
from jarvis.security.anomaly import AnomalyMonitor

# Security Engine Singletons
vault = AESVault()
permission_manager = PermissionManager()
sensitive_gate = SensitiveActionGate()
anomaly_monitor = AnomalyMonitor()

__all__ = [
    "AESVault",
    "PermissionManager",
    "SensitiveActionGate",
    "AnomalyMonitor",
    "vault",
    "permission_manager",
    "sensitive_gate",
    "anomaly_monitor",
]
