"""API request models"""
from typing import Optional, List
from pydantic import BaseModel, Field
from ...models.schemas import BrandMonitorConfig


class BrandCreate(BaseModel):
    """Request model for creating a brand"""
    name: str = Field(..., min_length=1, max_length=200)
    domain: str = Field(..., min_length=1, max_length=200)
    keywords: List[str] = Field(default_factory=list)
    email_patterns: List[str] = Field(default_factory=list)
    regex_patterns: List[str] = Field(default_factory=list)
    typosquat_variants: List[str] = Field(default_factory=list)
    slack_webhook: Optional[str] = None
    alert_email: Optional[str] = None
    monitor_config: BrandMonitorConfig = Field(default_factory=BrandMonitorConfig)


class BrandUpdate(BaseModel):
    """Request model for updating a brand"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    keywords: Optional[List[str]] = None
    email_patterns: Optional[List[str]] = None
    regex_patterns: Optional[List[str]] = None
    typosquat_variants: Optional[List[str]] = None
    slack_webhook: Optional[str] = None
    alert_email: Optional[str] = None
    monitor_config: Optional[BrandMonitorConfig] = None
    active: Optional[bool] = None


class TriggerMonitorRequest(BaseModel):
    """Request model for triggering monitors"""
    brand_id: Optional[str] = Field(None, description="Brand ID to scan. If None, scans all active brands")


class UpdateHitStatusRequest(BaseModel):
    """Request model for updating hit processing status"""
    status: str = Field(..., description="New status: pending, reviewed, false_positive")
    notes: Optional[str] = Field(None, description="Optional notes about the status change")
    
    def validate_status(self) -> str:
        """Validate status value"""
        valid_statuses = {"pending", "reviewed", "false_positive"}
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status: {self.status}. Must be one of {valid_statuses}")
        return self.status


class EnrichmentConfigUpdate(BaseModel):
    """Request model for updating enrichment configuration"""
    enabled: Optional[bool] = None
    use_anthropic: Optional[bool] = None
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_model: Optional[str] = None
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    anthropic_api_key: Optional[str] = None
    anthropic_model: Optional[str] = None
    alert_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    suppress_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    escalate_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)


class CircuitBreakerResetRequest(BaseModel):
    """Request model for resetting circuit breaker"""
    monitor_type: str = Field(..., description="Monitor type to reset: pastebin, github, hibp, reddit")

# Made with Bob
