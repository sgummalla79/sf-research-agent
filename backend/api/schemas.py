from typing import Literal, Optional
from pydantic import BaseModel


class StartRequest(BaseModel):
    brief: str
    # "chat" = free-form LLM conversation; "agent_flow" = structured pipeline
    session_type: Literal["chat", "agent_flow"] = "agent_flow"
    # Required when session_type == "agent_flow"
    flow_id: str = "architect"
    # Required when session_type == "chat"
    chat_model: str = "claude-sonnet-4-6"
    extended_thinking: bool = False


class ChatMessageRequest(BaseModel):
    """Sent by the client to continue a free-form chat session."""
    message: str


class ReplyRequest(BaseModel):
    # List of answers — one per question in the group (positional order).
    answers: list[str]


class SessionResponse(BaseModel):
    session_id: str
