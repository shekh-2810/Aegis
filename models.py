from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class Article(BaseModel):
    id: Optional[str] = None
    title: str
    category: str
    description: str
    image: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    featured: bool = False
    trending: bool = False


class Alert(BaseModel):
    id: Optional[str] = None
    title: str
    severity: str
    description: str
    date: Optional[str] = None


class SubscribeRequest(BaseModel):
    email: EmailStr


class HomepageResponse(BaseModel):
    breaking_news: List[dict]
    featured_story: Optional[dict]
    trending: List[dict]
    latest_articles: List[dict]
    alerts: List[dict]


# ---- Auth ----

class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- Incidents ----

class IncidentDetailsUpdate(BaseModel):
    incident_type: Optional[str] = None
    location: Optional[str] = None
    occurred_at: Optional[str] = None
    description: Optional[str] = Field(default=None, max_length=1000)


class IncidentAdditionalUpdate(BaseModel):
    financial_loss: Optional[bool] = None
    amount_lost: Optional[float] = Field(default=None, ge=0)
    contacted_platform: Optional[bool] = None
    platform_response: Optional[str] = None
    notes: Optional[str] = None


class IncidentGenerateReportRequest(BaseModel):
    report_type: str = Field(default="standard")
    report_language: str = Field(default="English")


class IncidentOut(BaseModel):
    id: str
    tracking_code: str
    user_id: Optional[str] = None
    status: str
    incident_type: Optional[str] = None
    location: Optional[str] = None
    occurred_at: Optional[str] = None
    description: Optional[str] = None
    financial_loss: Optional[bool] = None
    amount_lost: Optional[float] = None
    evidence_files: List[dict] = Field(default_factory=list)
    contacted_platform: Optional[bool] = None
    platform_response: Optional[str] = None
    notes: Optional[str] = None
    report_type: Optional[str] = None
    report_language: Optional[str] = None
    generated_report: Optional[dict] = None
    created_at: str
    updated_at: str
