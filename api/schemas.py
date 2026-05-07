from pydantic import BaseModel


class StartRequest(BaseModel):
    brief: str


class ReplyRequest(BaseModel):
    # List of answers — one per question in the group (positional order).
    # Single-question replies are still a one-item list.
    answers: list[str]


class SessionResponse(BaseModel):
    session_id: str
