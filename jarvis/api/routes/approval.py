"""
FastAPI Endpoint for Human Confirmation Approval Tokens.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jarvis.security import sensitive_gate
from jarvis.utils.logger import get_logger

logger = get_logger("API_Approval")
router = APIRouter(prefix="/v1", tags=["Approval Gate"])


class ApprovalRequest(BaseModel):
    confirmation_token: str


class ApprovalResponse(BaseModel):
    confirmed: bool
    message: str


@router.post("/plan/{plan_id}/confirm", response_model=ApprovalResponse)
async def confirm_sensitive_step(plan_id: str, request: ApprovalRequest):
    """
    Confirms a pending sensitive action step using a human confirmation token.
    """
    token = request.confirmation_token
    logger.info(f"Received confirmation request for plan '{plan_id}' with token '{token}'")
    success = sensitive_gate.confirm_action(token)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired confirmation token")

    return ApprovalResponse(confirmed=True, message=f"Token '{token}' approved successfully for plan '{plan_id}'")
