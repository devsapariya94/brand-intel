"""API response models"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from ...models.schemas import BrandMonitorConfig, MatchDetails


class BrandStats(BaseModel):
    """Brand statistics"""
    total_hits: int = 0
    hits_last_24h: int = 0
    last_scan: Optional[datetime] = None
    last_hit: Optional[datetime] = None


class BrandResponse(BaseModel):
    """Response model for brand"""
    id: str
    name: str
    domain: str
    keywords: List[str]
    email_patterns: List[str]
    regex_patterns: List[str]
    typosquat_variants: List[str]
    slack_webhook: Optional[str]
    alert_email: Optional[str]
    monitor_config: BrandMonitorConfig
    active: bool
    created_at: datetime
    updated_at: datetime
    stats: Optional[BrandStats] = None


class MonitorStatus(BaseModel):
    """Monitor status information"""
    name: str
    type: str
    enabled: bool
    available: bool
    rate_limit_remaining: int
    rate_limit_total: int
    last_run: Optional[datetime] = None
    success_rate: float = 0.0
    avg_execution_time: float = 0.0


class CircuitBreakerState(BaseModel):
    """Circuit breaker state"""
    state: str  # "closed", "open", "half_open"
    failure_count: int
    last_failure: Optional[datetime] = None
    next_retry: Optional[datetime] = None


class MonitorsStatusResponse(BaseModel):
    """Response for monitors status"""
    monitors: List[MonitorStatus]
    circuit_breaker: Dict[str, CircuitBreakerState]
    last_scan: Optional[datetime] = None
    next_scan: Optional[datetime] = None


class MonitorResultResponse(BaseModel):
    """Response for single monitor run"""
    monitor_type: str
    brand_id: str
    brand_name: str
    hits_found: int
    hits_stored: int
    execution_time_seconds: float
    status: str
    started_at: datetime
    completed_at: datetime
    error: Optional[str] = None


class ScanResultResponse(BaseModel):
    """Response for full scan"""
    scan_id: str
    brands_scanned: int
    successful_scans: int
    failed_scans: int
    total_hits_found: int
    total_hits_stored: int
    results: List[MonitorResultResponse]
    started_at: datetime
    completed_at: datetime


class MonitorRunResponse(BaseModel):
    """Response for monitor run history"""
    id: str
    monitor_type: str
    brand_id: Optional[str] = None
    brand_name: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    hits_found: int
    hits_stored: int
    error_message: Optional[str] = None
    execution_time_seconds: float
    api_calls_made: int


class RawHitResponse(BaseModel):
    """Response for raw hit"""
    id: str
    brand_id: str
    brand_name: str
    source: str
    source_url: str
    raw_content: str
    content_preview: str
    detected_at: datetime
    match_details: MatchDetails
    processing_status: str
    created_at: datetime
    updated_at: datetime
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    notes: Optional[str] = None


class PaginatedHitsResponse(BaseModel):
    """Paginated hits response"""
    hits: List[RawHitResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


class TimelinePoint(BaseModel):
    """Timeline data point"""
    date: str
    count: int


class KeywordStat(BaseModel):
    """Keyword statistics"""
    keyword: str
    count: int


class HitsStatsResponse(BaseModel):
    """Hits statistics"""
    total_hits: int
    by_source: Dict[str, int]
    by_status: Dict[str, int]
    by_brand: Dict[str, int]
    timeline: List[TimelinePoint]
    top_keywords: List[KeywordStat]


class ComponentHealth(BaseModel):
    """Component health status"""
    status: str  # "healthy", "degraded", "unhealthy"
    available: bool
    last_check: datetime
    error: Optional[str] = None
    metrics: Dict[str, Any] = {}


class DLQHealth(BaseModel):
    """DLQ health status"""
    pending: int
    failed: int
    retrying: int


class DetailedHealthResponse(BaseModel):
    """Detailed system health"""
    status: str
    database: ComponentHealth
    monitors: Dict[str, ComponentHealth]
    circuit_breaker: Dict[str, CircuitBreakerState]
    dlq: DLQHealth
    enrichment: ComponentHealth
    uptime_seconds: float
    last_scan: Optional[datetime] = None


class MetricsResponse(BaseModel):
    """System metrics"""
    total_brands: int
    active_brands: int
    total_hits: int
    hits_last_24h: int
    monitor_runs_last_24h: int
    success_rate: float
    avg_execution_time: float
    dlq_pending: int
    enrichment_queue: int


class EnrichmentConfigResponse(BaseModel):
    """Enrichment configuration"""
    enabled: bool
    use_anthropic: bool
    llm_model: str
    llm_temperature: float
    alert_threshold: float
    suppress_threshold: float
    escalate_threshold: float


class EnrichmentStatsResponse(BaseModel):
    """Enrichment statistics"""
    total_processed: int
    alerts_sent: int
    suppressed: int
    escalated: int
    avg_processing_time: float
    estimated_cost: float


class DLQItemResponse(BaseModel):
    """DLQ item"""
    id: str
    brand_id: str
    brand_name: str
    source: str
    error: str
    retry_count: int
    max_retries: int
    created_at: datetime
    last_retry: Optional[datetime] = None
    status: str


class LogEntry(BaseModel):
    """Log entry"""
    timestamp: datetime
    level: str
    logger: str
    message: str
    extra: Dict[str, Any] = {}


class MonitorHealthResponse(BaseModel):
    """Monitor health details"""
    monitor_type: str
    status: str
    available: bool
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_execution_time: float
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None
    circuit_breaker_state: str

# Made with Bob
