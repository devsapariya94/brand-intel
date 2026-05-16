"""Data schemas for AI enrichment layer"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
from bson import ObjectId


class ThreatType(str, Enum):
    """Types of security threats"""
    CREDENTIAL_LEAK = "credential_leak"
    PII_EXPOSURE = "pii_exposure"
    FINANCIAL_DATA = "financial_data"
    API_KEY_LEAK = "api_key_leak"
    SOURCE_CODE_LEAK = "source_code_leak"
    DATABASE_DUMP = "database_dump"
    CONFIGURATION_LEAK = "configuration_leak"
    INTERNAL_DOCUMENT = "internal_document"


class Severity(str, Enum):
    """Severity levels for threats"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendedAction(str, Enum):
    """LLM recommended actions"""
    ALERT = "ALERT"
    SUPPRESS = "SUPPRESS"
    ESCALATE_HUMAN = "ESCALATE_HUMAN"


class AlertDecision(str, Enum):
    """Final alert decision"""
    ALERT = "ALERT"
    SUPPRESS = "SUPPRESS"
    ESCALATE = "ESCALATE"


class EvaluationResult(BaseModel):
    """LLM evaluation result for a raw hit"""
    is_threat: bool
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    threat_types: List[ThreatType] = []
    reasoning: str
    recommended_action: RecommendedAction

    # Metadata
    model_used: str
    provider: str
    evaluation_time_ms: int

    class Config:
        use_enum_values = True


class EnrichmentResult(BaseModel):
    """Complete enrichment result stored in database"""
    hit_id: str
    brand_id: str
    evaluation: EvaluationResult
    decision: AlertDecision
    decision_reasoning: str

    # Timestamps
    enriched_at: datetime
    processing_time_ms: int

    # Cost tracking
    estimated_cost_usd: float

    class Config:
        use_enum_values = True
        json_encoders = {ObjectId: str}


class ProcessingStats(BaseModel):
    """Statistics for batch processing"""
    total_processed: int
    alerts_sent: int
    suppressed: int
    escalated: int
    failed: int
    processing_time_ms: int

    @property
    def alert_rate(self) -> float:
        """Calculate alert rate"""
        if self.total_processed == 0:
            return 0.0
        return self.alerts_sent / self.total_processed

    @property
    def suppression_rate(self) -> float:
        """Calculate suppression rate"""
        if self.total_processed == 0:
            return 0.0
        return self.suppressed / self.total_processed


class HumanReviewItem(BaseModel):
    """Item queued for human review"""
    hit_id: str
    enrichment_id: str
    escalation_reason: str
    status: str = "pending"  # pending, reviewed, resolved
    assigned_to: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_decision: Optional[AlertDecision] = None
    review_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        json_encoders = {ObjectId: str}


# MongoDB Index Definitions for new collections
ENRICHMENT_INDEXES = {
    "enriched_hits": [
        {"keys": [("hit_id", 1)], "unique": True},
        {"keys": [("brand_id", 1), ("enriched_at", -1)]},
        {"keys": [("decision", 1), ("enriched_at", -1)]},
        {"keys": [("evaluation.severity", 1)]},
        {"keys": [("enriched_at", -1)]},
    ],
    "human_review_queue": [
        {"keys": [("hit_id", 1)]},
        {"keys": [("status", 1), ("created_at", 1)]},
        {"keys": [("assigned_to", 1), ("status", 1)]},
    ],
}


async def create_enrichment_indexes(db):
    """Create MongoDB indexes for enrichment collections"""
    for collection_name, indexes in ENRICHMENT_INDEXES.items():
        collection = db[collection_name]
        for index_spec in indexes:
            await collection.create_index(
                index_spec["keys"],
                unique=index_spec.get("unique", False)
            )


# Made with Bob
