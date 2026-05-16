"""Configuration management for monitoring daemon"""
import os
from typing import Optional, List
from pydantic import BaseModel, Field
from ..enrichment.llm import LLMConfig


class DaemonConfig(BaseModel):
    """Daemon configuration from environment variables"""

    # MongoDB
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URI"
    )

    # Scheduling
    scan_interval_minutes: int = Field(
        default=15,
        description="Interval between scans in minutes",
        ge=1,
        le=1440
    )

    # Concurrency
    max_concurrent_brands: int = Field(
        default=10,
        description="Maximum number of brands to scan concurrently",
        ge=1,
        le=100
    )

    max_concurrent_monitors: int = Field(
        default=4,
        description="Maximum number of monitors to run per brand",
        ge=1,
        le=10
    )

    # Monitor Rate Limits (requests per minute)
    pastebin_rate_limit: int = Field(default=60, ge=1)
    github_rate_limit: int = Field(default=30, ge=1)
    reddit_rate_limit: int = Field(default=60, ge=1)
    hibp_rate_limit: int = Field(default=60, ge=1)

    # Timeouts
    monitor_timeout_seconds: int = Field(default=30, ge=5, le=300)

    # Retry Configuration
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_base_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    retry_max_delay: float = Field(default=60.0, ge=1.0, le=300.0)

    # Circuit Breaker
    circuit_breaker_enabled: bool = Field(default=True)
    circuit_breaker_failure_threshold: int = Field(default=5, ge=1, le=20)
    circuit_breaker_timeout_seconds: int = Field(default=300, ge=60, le=3600)

    # Alerting
    slack_webhook_url: Optional[str] = Field(
        default=None,
        description="Slack webhook URL for alerts"
    )

    alert_email: Optional[str] = Field(
        default=None,
        description="Email address for critical alerts"
    )

    alert_on_monitor_failure: bool = Field(
        default=True,
        description="Send alerts when monitors fail"
    )

    alert_failure_threshold: int = Field(
        default=3,
        description="Number of consecutive failures before alerting",
        ge=1,
        le=10
    )

    # Health Check
    health_check_enabled: bool = Field(default=True)
    health_check_port: int = Field(default=8001, ge=1024, le=65535)

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )

    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Dead Letter Queue
    dlq_enabled: bool = Field(
        default=True,
        description="Enable dead letter queue for failed hits"
    )

    dlq_max_retries: int = Field(
        default=3,
        description="Maximum retries for DLQ items",
        ge=0,
        le=10
    )

    # API Keys
    pastebin_api_key: Optional[str] = Field(default=None)
    github_token: Optional[str] = Field(default=None)
    reddit_client_id: Optional[str] = Field(default=None)
    reddit_client_secret: Optional[str] = Field(default=None)
    hibp_api_key: Optional[str] = Field(default=None)

    # Enrichment
    enrichment_enabled: bool = Field(default=True)
    use_anthropic: bool = Field(default=False)
    llm_api_key: Optional[str] = Field(default=None)
    llm_base_url: Optional[str] = Field(default=None)
    llm_model: str = Field(default="gpt-3.5-turbo")
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    anthropic_api_key: Optional[str] = Field(default=None)
    anthropic_model: str = Field(default="claude-3-haiku-20240307")
    anthropic_temperature: float = Field(default=0.3, ge=0.0, le=2.0)

    @classmethod
    def from_env(cls) -> "DaemonConfig":
        """Load configuration from environment variables"""
        return cls(
            # MongoDB
            mongodb_uri=os.getenv("MONGODB_URI", "mongodb://localhost:27017"),

            # Scheduling
            scan_interval_minutes=int(os.getenv("SCAN_INTERVAL_MINUTES", "15")),

            # Concurrency
            max_concurrent_brands=int(os.getenv("MAX_CONCURRENT_BRANDS", "10")),
            max_concurrent_monitors=int(os.getenv("MAX_CONCURRENT_MONITORS", "4")),

            # Rate Limits
            pastebin_rate_limit=int(os.getenv("PASTEBIN_RATE_LIMIT", "60")),
            github_rate_limit=int(os.getenv("GITHUB_RATE_LIMIT", "30")),
            reddit_rate_limit=int(os.getenv("REDDIT_RATE_LIMIT", "60")),
            hibp_rate_limit=int(os.getenv("HIBP_RATE_LIMIT", "60")),

            # Timeouts
            monitor_timeout_seconds=int(os.getenv("MONITOR_TIMEOUT_SECONDS", "30")),

            # Retry
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            retry_base_delay=float(os.getenv("RETRY_BASE_DELAY", "1.0")),
            retry_max_delay=float(os.getenv("RETRY_MAX_DELAY", "60.0")),

            # Circuit Breaker
            circuit_breaker_enabled=os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true",
            circuit_breaker_failure_threshold=int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5")),
            circuit_breaker_timeout_seconds=int(os.getenv("CIRCUIT_BREAKER_TIMEOUT_SECONDS", "300")),

            # Alerting
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            alert_email=os.getenv("ALERT_EMAIL"),
            alert_on_monitor_failure=os.getenv("ALERT_ON_MONITOR_FAILURE", "true").lower() == "true",
            alert_failure_threshold=int(os.getenv("ALERT_FAILURE_THRESHOLD", "3")),

            # Health Check
            health_check_enabled=os.getenv("HEALTH_CHECK_ENABLED", "true").lower() == "true",
            health_check_port=int(os.getenv("HEALTH_CHECK_PORT", "8001")),

            # Logging
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),

            # DLQ
            dlq_enabled=os.getenv("DLQ_ENABLED", "true").lower() == "true",
            dlq_max_retries=int(os.getenv("DLQ_MAX_RETRIES", "3")),

            # API Keys
            pastebin_api_key=os.getenv("PASTEBIN_API_KEY"),
            github_token=os.getenv("GITHUB_TOKEN"),
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            hibp_api_key=os.getenv("HIBP_API_KEY"),

            # Enrichment
            enrichment_enabled=os.getenv("ENRICHMENT_ENABLED", "true").lower() == "true",
            use_anthropic=os.getenv("USE_ANTHROPIC", "false").lower() == "true",
            llm_api_key=os.getenv("LLM_API_KEY"),
            llm_base_url=os.getenv("LLM_BASE_URL"),
            llm_model=os.getenv("LLM_MODEL", "gpt-3.5-turbo"),
            llm_temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            anthropic_temperature=float(os.getenv("ANTHROPIC_TEMPERATURE", "0.3")),
        )

    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration based on use_anthropic flag"""
        if self.use_anthropic:
            return LLMConfig(
                api_key=self.anthropic_api_key,
                model=self.anthropic_model,
                temperature=self.anthropic_temperature,
            )
        else:
            return LLMConfig(
                api_key=self.llm_api_key,
                base_url=self.llm_base_url,
                model=self.llm_model,
                temperature=self.llm_temperature,
            )

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of warnings"""
        warnings = []

        if self.scan_interval_minutes < 5:
            warnings.append("Scan interval < 5 minutes may cause rate limiting")

        if self.max_concurrent_brands > 20:
            warnings.append("High concurrency may overwhelm external APIs")

        if not self.slack_webhook_url and not self.alert_email:
            warnings.append("No alerting configured - consider adding Slack or email")

        if self.circuit_breaker_failure_threshold < 3:
            warnings.append("Low circuit breaker threshold may cause false positives")

        if not self.pastebin_api_key:
            warnings.append("PASTEBIN_API_KEY not set - Pastebin monitor will fail")

        if not self.github_token:
            warnings.append("GITHUB_TOKEN not set - GitHub monitor will fail")

        if not self.reddit_client_id or not self.reddit_client_secret:
            warnings.append("Reddit credentials not set - Reddit monitor will fail")

        if not self.hibp_api_key:
            warnings.append("HIBP_API_KEY not set - HIBP monitor will fail")

        if self.enrichment_enabled and not self.use_anthropic:
            if not self.llm_api_key:
                warnings.append("LLM_API_KEY not set - enrichment will fail")
            if not self.llm_base_url:
                warnings.append("LLM_BASE_URL not set - enrichment will fail")

        if self.enrichment_enabled and self.use_anthropic:
            if not self.anthropic_api_key:
                warnings.append("ANTHROPIC_API_KEY not set - enrichment will fail")

        return warnings

    class Config:
        """Pydantic config"""
        validate_assignment = True

# Made with Bob
