"""Enrichment service for processing hits with LLM"""
import json
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..enrichment.llm.base import (
    BaseLLMProvider, ChatMessage, ChatCompletionResponse, LLMConfig
)
from ..enrichment.llm.generic_provider import GenericLLMProvider
from ..enrichment.llm.anthropic_provider import AnthropicProvider
from ..models.enrichment_schemas import (
    EvaluationResult, EnrichmentResult, AlertDecision, 
    RecommendedAction, Severity, ThreatType
)

logger = logging.getLogger(__name__)

# System prompt for threat evaluation
ENRICHMENT_SYSTEM_PROMPT = """You are a security threat analyst for a brand monitoring system.
Your job is to evaluate whether a detected hit represents a genuine security threat.

Analyze the raw content and determine:
1. Is this a genuine threat? (is_threat)
2. What type of threat is it? (threat_types)
3. How severe is it? (severity: CRITICAL, HIGH, MEDIUM, LOW)
4. How confident are you? (confidence: 0.0-1.0)
5. What action should be taken? (recommended_action: ALERT, SUPPRESS, ESCALATE_HUMAN)
6. Explain your reasoning. (reasoning)

Return ONLY a valid JSON object with this exact structure:
{
    "is_threat": true/false,
    "severity": "CRITICAL"|"HIGH"|"MEDIUM"|"LOW",
    "confidence": 0.0-1.0,
    "threat_types": ["credential_leak", "pii_exposure", ...],
    "reasoning": "Your detailed explanation...",
    "recommended_action": "ALERT"|"SUPPRESS"|"ESCALATE_HUMAN"
}

Valid threat_types: credential_leak, pii_exposure, financial_data, api_key_leak, source_code_leak, database_dump, configuration_leak, internal_document
"""

class EnrichmentService:
    """Service for enriching hits with LLM-based threat analysis"""
    
    def __init__(self, db_client: AsyncIOMotorClient, config, alert_manager=None):
        self.db = db_client.brand_intel
        self.config = config
        self._provider: Optional[BaseLLMProvider] = None
        self.alert_manager = alert_manager
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the LLM provider based on config"""
        llm_config = self.config.get_llm_config()
        if not llm_config.api_key and not llm_config.base_url:
            logger.warning("No LLM API key or base URL configured")
            return
        
        try:
            if self.config.use_anthropic:
                self._provider = AnthropicProvider(llm_config)
                logger.info(f"Anthropic LLM provider initialized: {llm_config.model}")
            else:
                self._provider = GenericLLMProvider(llm_config)
                logger.info(f"Generic LLM provider initialized: {llm_config.model} @ {llm_config.base_url}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM provider: {e}")
            self._provider = None
    
    async def process_hit(self, hit_id: str, brand_id: str) -> Optional[EnrichmentResult]:
        """Process a single hit through the LLM enrichment pipeline"""
        if not self._provider:
            logger.error("LLM provider not available")
            return None
        
        # Check if already enriched
        existing = await self.db.enriched_hits.find_one({"hit_id": hit_id})
        if existing:
            logger.info(f"Hit {hit_id} already enriched, skipping")
            return None
        
        # Fetch the raw hit
        try:
            from bson import ObjectId
            hit = await self.db.raw_hits.find_one({"_id": ObjectId(hit_id)})
        except Exception:
            hit = await self.db.raw_hits.find_one({"_id": hit_id})
        
        if not hit:
            logger.error(f"Hit {hit_id} not found")
            return None
        
        # Fetch brand details
        brand = None
        hit_brand_id = hit.get("brand_id")
        if hit_brand_id:
            brand = await self.db.brands.find_one({"_id": hit_brand_id})
            if not brand:
                try:
                    brand = await self.db.brands.find_one({"_id": ObjectId(hit_brand_id)})
                except Exception:
                    brand = None
        
        if not brand:
            brand = {"name": "Unknown", "domain": ""}
        
        # Build the prompt
        content_preview = hit.get("raw_content", "")[:2000]
        match_details = hit.get("match_details", {})
        
        user_prompt = f"""Brand: {brand.get('name', 'Unknown')}
Domain: {brand.get('domain', 'N/A')}
Source: {hit.get('source', 'unknown')}
Source URL: {hit.get('source_url', 'N/A')}
Matched Keywords: {', '.join(match_details.get('matched_keywords', []))}

Raw Content:
{content_preview}

Evaluate this hit and return your analysis as JSON."""
        
        messages = [
            ChatMessage(role="system", content=ENRICHMENT_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ]
        
        start_time = time.time()
        
        try:
            response = await self._provider.chat_completion(
                messages,
                temperature=self.config.llm_temperature
            )
            
            processing_time_ms = int((time.time() - start_time) * 1000)

            await self._record_llm_call(
                hit_id=hit_id,
                brand_id=str(hit_brand_id or brand_id),
                provider=response.provider,
                model=response.model,
                status="success",
                latency_ms=processing_time_ms,
                response_preview=response.content[:1000],
            )
            
            # Parse the LLM response
            evaluation = self._parse_llm_response(response.content, response.model, response.provider, processing_time_ms)
            
            if not evaluation:
                logger.error(f"Failed to parse LLM response for hit {hit_id}")
                return None
            
            # Apply decision thresholds
            decision = self._apply_thresholds(evaluation)
            
            # Build enrichment result
            result = EnrichmentResult(
                hit_id=hit_id,
                brand_id=str(brand_id),
                evaluation=evaluation,
                decision=decision,
                decision_reasoning=evaluation.reasoning,
                enriched_at=datetime.now(timezone.utc),
                processing_time_ms=processing_time_ms,
                estimated_cost_usd=0.0  # Would need token counting for accurate cost
            )
            
            alert_context = {
                "brand_name": brand.get("name", "Unknown"),
                "source": hit.get("source", "unknown"),
                "source_url": hit.get("source_url", ""),
                "matched_keywords": match_details.get("matched_keywords", [])
            }
            
            # Store in database
            await self._store_result(result, alert_context)
            
            logger.info(f"Enriched hit {hit_id}: decision={decision}, severity={evaluation.severity}, confidence={evaluation.confidence:.2f}")
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            provider_name = "anthropic" if self.config.use_anthropic else (self.config.llm_base_url or "openai")
            model_name = self.config.anthropic_model if self.config.use_anthropic else self.config.llm_model
            await self._record_llm_call(
                hit_id=hit_id,
                brand_id=str(hit_brand_id or brand_id),
                provider=provider_name,
                model=model_name,
                status="failed",
                latency_ms=processing_time_ms,
                error=str(e),
            )
            logger.error(f"Enrichment failed for hit {hit_id}: {e}", exc_info=True)
            return None

    async def _record_llm_call(
        self,
        hit_id: str,
        brand_id: str,
        provider: str,
        model: str,
        status: str,
        latency_ms: int,
        response_preview: str = "",
        error: Optional[str] = None,
    ):
        """Persist LLM call telemetry for dashboards and debugging."""
        try:
            await self.db.llm_calls.insert_one({
                "hit_id": hit_id,
                "brand_id": brand_id,
                "provider": provider,
                "model": model,
                "status": status,
                "latency_ms": latency_ms,
                "response_preview": response_preview,
                "error": error,
                "created_at": datetime.now(timezone.utc),
            })
        except Exception as telemetry_err:
            logger.error(f"Failed to record LLM call telemetry: {telemetry_err}")
    
    def _parse_llm_response(self, content: str, model: str, provider: str, processing_time_ms: int) -> Optional[EvaluationResult]:
        """Parse LLM response into EvaluationResult"""
        try:
            # Try to extract JSON from the response
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(json_str)
            
            # Parse threat types
            threat_types = []
            for tt in data.get("threat_types", []):
                try:
                    threat_types.append(ThreatType(tt))
                except ValueError:
                    logger.warning(f"Unknown threat type: {tt}")
            
            return EvaluationResult(
                is_threat=data.get("is_threat", False),
                severity=Severity(data.get("severity", "LOW")),
                confidence=float(data.get("confidence", 0.5)),
                threat_types=threat_types,
                reasoning=data.get("reasoning", "No reasoning provided"),
                recommended_action=RecommendedAction(data.get("recommended_action", "ESCALATE_HUMAN")),
                model_used=model,
                provider=provider,
                evaluation_time_ms=processing_time_ms
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return None
    
    def _apply_thresholds(self, evaluation: EvaluationResult) -> AlertDecision:
        """Apply confidence thresholds to make final decision"""
        if evaluation.confidence >= 0.85 and evaluation.recommended_action == RecommendedAction.ALERT:
            return AlertDecision.ALERT
        elif evaluation.confidence >= 0.70:
            return AlertDecision.ALERT
        elif evaluation.confidence >= 0.60:
            return AlertDecision.ESCALATE
        else:
            return AlertDecision.SUPPRESS
    
    async def _store_result(self, result: EnrichmentResult, alert_context: dict = None):
        """Store enrichment result in MongoDB"""
        doc = result.dict()
        doc["_id"] = f"enrich_{result.hit_id}"
        
        await self.db.enriched_hits.update_one(
            {"hit_id": result.hit_id},
            {"$set": doc},
            upsert=True
        )
        
        # Update raw hit processing status based on decision
        try:
            from bson import ObjectId
            hit_oid = ObjectId(result.hit_id)
        except Exception:
            hit_oid = result.hit_id
        
        status_map = {
            AlertDecision.ALERT: "reviewed",
            AlertDecision.SUPPRESS: "false_positive",
            AlertDecision.ESCALATE: "pending",
        }
        
        await self.db.raw_hits.update_one(
            {"_id": hit_oid},
            {"$set": {
                "processing_status": status_map.get(result.decision, "pending"),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        # Add to human review queue if escalated
        if result.decision == AlertDecision.ESCALATE:
            await self.db.human_review_queue.insert_one({
                "hit_id": result.hit_id,
                "enrichment_id": doc["_id"],
                "escalation_reason": result.decision_reasoning,
                "status": "pending",
                "created_at": datetime.now(timezone.utc)
            })
        
        # Send alert for confirmed threats
        if result.decision == AlertDecision.ALERT and self.alert_manager and alert_context:
            severity_str = result.evaluation.severity.value if hasattr(result.evaluation.severity, 'value') else str(result.evaluation.severity)
            threat_types_str = [t.value if hasattr(t, 'value') else str(t) for t in result.evaluation.threat_types]
            
            await self.alert_manager.alert_threat_detected(
                hit_id=result.hit_id,
                brand_name=alert_context.get("brand_name", "Unknown"),
                source=alert_context.get("source", "unknown"),
                source_url=alert_context.get("source_url", ""),
                severity=severity_str,
                confidence=result.evaluation.confidence,
                threat_types=threat_types_str,
                reasoning=result.evaluation.reasoning,
                matched_keywords=alert_context.get("matched_keywords", []),
            )
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics"""
        total = await self.db.enriched_hits.count_documents({})
        alerts = await self.db.enriched_hits.count_documents({"decision": "ALERT"})
        suppressed = await self.db.enriched_hits.count_documents({"decision": "SUPPRESS"})
        escalated = await self.db.enriched_hits.count_documents({"decision": "ESCALATE"})
        
        # Average processing time
        pipeline = [
            {"$group": {"_id": None, "avg_time": {"$avg": "$processing_time_ms"}}}
        ]
        avg_result = await self.db.enriched_hits.aggregate(pipeline).to_list(length=1)
        avg_time = avg_result[0]["avg_time"] / 1000 if avg_result else 0.0
        
        return {
            "total_processed": total,
            "alerts_sent": alerts,
            "suppressed": suppressed,
            "escalated": escalated,
            "avg_processing_time": avg_time,
            "estimated_cost": 0.0  # Would need token tracking
        }
    
    async def process_pending_batch(self, batch_size: int = 10) -> int:
        """Process a batch of pending hits"""
        pending_hits = await self.db.raw_hits.find(
            {"processing_status": "pending"}
        ).sort("detected_at", 1).limit(batch_size).to_list(length=batch_size)
        
        processed = 0
        for hit in pending_hits:
            hit_id = str(hit["_id"])
            brand_id = hit.get("brand_id", "")
            
            # Skip if already enriched
            existing = await self.db.enriched_hits.find_one({"hit_id": hit_id})
            if existing:
                continue
            
            result = await self.process_hit(hit_id, str(brand_id))
            if result:
                processed += 1
            
            # Small delay to avoid rate limiting
            import asyncio
            await asyncio.sleep(0.5)
        
        return processed
