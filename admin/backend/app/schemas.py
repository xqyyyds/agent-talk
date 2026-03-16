from datetime import datetime
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class AdminUserOut(BaseModel):
    id: int
    username: str
    status: str
    created_at: datetime


class AdminUserUpdate(BaseModel):
    username: str | None = None
    status: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangeUsernameRequest(BaseModel):
    new_username: str = Field(min_length=3, max_length=64)


class ReasonRequest(BaseModel):
    reason: str = ""


class DashboardOverview(BaseModel):
    total_users: int
    total_agents: int
    total_questions: int
    total_answers: int
    today_users: int
    today_questions: int
    today_answers: int
    login_events_24h: int
    active_users_24h: int
    online_users_5m: int
    online_window_seconds: int
