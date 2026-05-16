"""MongoDB schemas and Pydantic models for the monitors component"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class BrandMonitorConfig(BaseModel):
    """Per-brand monitor enablement configuration"""
    pastebin_enabled: bool = True
    github_enabled: bool = True
    hibp_enabled: bool = True
    reddit_enabled: bool = True
    scan_frequency_minutes: int = 15


class Brand(BaseModel):
    """Brand model for MongoDB"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    name: str
    domain: str
    keywords: List[str] = []
    email_patterns: List[str] = []
    regex_patterns: List[str] = []
    typosquat_variants: List[str] = []
    slack_webhook: Optional[str] = None
    alert_email: Optional[str] = None
    monitor_config: BrandMonitorConfig = Field(default_factory=BrandMonitorConfig)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class MatchLocation(BaseModel):
    """Location of a match in content"""
    keyword: str
    start_index: int
    end_index: int
    context: str


class MatchDetails(BaseModel):
    """Details about keyword matches"""
    matched_keywords: List[str] = []
    matched_patterns: List[str] = []
    match_type: str
    confidence_score: float
    match_locations: List[MatchLocation] = []


class RawHitDocument(BaseModel):
    """Raw hit document stored in MongoDB"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    brand_id: PyObjectId
    source: str
    source_url: str
    raw_content: str
    content_hash: str
    detected_at: datetime
    match_details: MatchDetails
    metadata: Dict[str, Any] = {}
    processing_status: str = "pending"
    deduplication_checked: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class MonitorRun(BaseModel):
    """Monitor run tracking"""
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    monitor_type: str
    brand_id: Optional[PyObjectId] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    hits_found: int = 0
    hits_stored: int = 0
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
    api_calls_made: int = 0
    rate_limit_hit: bool = False

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


MONGODB_INDEXES = {
    "brands": [
        {"keys": [("domain", 1)], "unique": True},
        {"keys": [("active", 1)]},
    ],
    "raw_hits": [
        {"keys": [("brand_id", 1), ("detected_at", -1)]},
        {"keys": [("content_hash", 1)], "unique": True},
        {"keys": [("source", 1), ("detected_at", -1)]},
        {"keys": [("processing_status", 1)]},
        {"keys": [("detected_at", -1)]},
    ],
    "monitor_runs": [
        {"keys": [("monitor_type", 1), ("started_at", -1)]},
        {"keys": [("brand_id", 1), ("started_at", -1)]},
        {"keys": [("status", 1), ("started_at", -1)]},
    ],
}


async def create_indexes(db):
    """Create MongoDB indexes"""
    for collection_name, indexes in MONGODB_INDEXES.items():
        collection = db[collection_name]
        for index_spec in indexes:
            await collection.create_index(
                index_spec["keys"],
                unique=index_spec.get("unique", False)
            )
