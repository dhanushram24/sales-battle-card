from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


class LeadInteraction(BaseModel):
    id: Optional[str] = None
    lead_id: str
    content: str = Field(..., description="Call note, transcript, email text, or meeting summary")
    interaction_type: Optional[str] = Field("note", description="call, email, note, whatsapp, meeting")
    direction: Optional[str] = Field("inbound", description="inbound (customer), outbound (rep), internal")
    created_at: Optional[datetime] = None

    @field_validator("created_at")
    @classmethod
    def normalize_date(cls, value):
        if value is None:
            return value
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class LeadInfo(BaseModel):
    id: str
    name: Optional[str] = "Unknown Contact"
    company: Optional[str] = "Unknown Company"
    status: Optional[str] = None
    stage: Optional[str] = None
    assigned_to: Optional[str] = None
    interactions: List[LeadInteraction] = Field(default_factory=list, max_length=2000)


class LeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    company: Optional[str] = Field(default=None, min_length=1, max_length=150)
    status: Optional[str] = Field(default=None, min_length=1, max_length=50)
    stage: Optional[str] = Field(default=None, min_length=1, max_length=50)
    assigned_to: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set or any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Provide at least one non-empty lead field")
        return self
