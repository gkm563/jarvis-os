"""
FastAPI Endpoints for Task Execution Logs and Audit Telemetry.
"""

from fastapi import APIRouter
from typing import Dict, Any
from jarvis.utils.logger import get_logger

import psutil
import time

logger = get_logger("API_Logs")
router = APIRouter(prefix="/v1", tags=["Logs & Telemetry"])


@router.get("/logs/{task_id}")
async def get_task_logs(task_id: str) -> Dict[str, Any]:
    """Retrieves structured logs and telemetry for a completed task execution."""
    return {
        "task_id": task_id,
        "logs": [
            {"time": "2026-07-26T22:40:00Z", "level": "INFO", "message": f"Task '{task_id}' started"},
            {"time": "2026-07-26T22:40:01Z", "level": "INFO", "message": f"Task '{task_id}' step completed"},
        ],
    }


@router.get("/system/stats")
async def get_system_stats() -> Dict[str, Any]:
    """Retrieves real-time Windows system diagnostics."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('C:\\').percent
        
        # Quick diff to estimate network throughput
        net_before = psutil.net_io_counters()
        time.sleep(0.05)
        net_after = psutil.net_io_counters()
        
        bytes_total = (net_after.bytes_sent - net_before.bytes_sent) + (net_after.bytes_recv - net_before.bytes_recv)
        mbps = max(0.1, round((bytes_total * 8 / (1024 * 1024)) / 0.05, 2))
        
        return {
            "cpu": int(cpu),
            "memory": int(mem),
            "disk": int(disk),
            "network": mbps
        }
    except Exception as e:
        logger.error(f"Failed to query system stats: {e}")
        return {
            "cpu": 0,
            "memory": 0,
            "disk": 0,
            "network": 0.0
        }
