export interface Brand {
  id: string
  name: string
  domain: string
  keywords: string[]
  email_patterns: string[]
  regex_patterns: string[]
  typosquat_variants: string[]
  slack_webhook: string | null
  alert_email: string | null
  active: boolean
  monitor_config: {
    github_enabled: boolean
    hackernews_enabled: boolean
    ransomware_enabled: boolean
    xposedornot_enabled: boolean
    intelx_enabled: boolean
  }
  stats: {
    total_hits: number
    hits_last_24h: number
  }
  created_at: string
  updated_at: string
}

export interface MonitorStatus {
  type: string
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  available: boolean
  success_rate: number
  avg_execution_time: number
  last_run: string | null
  total_runs: number
}

export interface CircuitBreakerState {
  state: 'closed' | 'open' | 'half_open'
  failure_count: number
  last_failure: string | null
}

export interface MonitorRun {
  id: string
  monitor_type: string
  brand_id: string
  brand_name: string
  status: string
  hits_found: number
  hits_stored: number
  hits_enriched: number
  execution_time_seconds: number
  started_at: string
  completed_at: string | null
  error: string | null
}

export interface Hit {
  id: string
  brand_id: string
  brand_name: string
  source: string
  source_url: string
  content_preview: string
  match_details: {
    matched_keywords: string[]
    match_context: string
  }
  processing_status: 'pending' | 'reviewed' | 'false_positive'
  enrichment: {
    decision: 'ALERT' | 'ESCALATE' | 'SUPPRESS' | null
    evaluation: {
      severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | null
      confidence: number | null
      reasoning: string
      threat_types: string[]
    }
    processed_at: string
  } | null
  detected_at: string
  created_at: string
}

export interface HitsResponse {
  hits: Hit[]
  total: number
  page: number
  limit: number
  has_next: boolean
  has_prev: boolean
}

export interface HitsStats {
  total_hits: number
  by_status: Record<string, number>
  by_source: Record<string, number>
  timeline: { date: string; count: number }[]
  top_keywords: { keyword: string; count: number }[]
}

export interface EnrichmentConfig {
  use_anthropic: boolean
  llm_model: string
  llm_temperature: number
  alert_threshold: number
  suppress_threshold: number
  escalate_threshold: number
}

export interface EnrichmentStats {
  total_processed: number
  alerts_sent: number
  suppressed: number
  escalated: number
  avg_processing_time: number
  estimated_cost: number
}

export interface LlmCallStats {
  total_calls: number
  success_rate: number
  avg_latency_ms: number
  by_provider: { provider: string; calls: number; avg_latency: number }[]
}

export interface LlmCall {
  id: string
  provider: string
  model: string
  status: string
  latency_ms: number
  hit_id: string
  error: string | null
  created_at: string
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  database: { status: string }
  monitors: Record<string, { status: string }>
  dlq: { pending: number; failed: number }
  uptime_seconds: number
  last_scan: string | null
}

export interface Metrics {
  total_brands: number
  total_hits: number
  success_rate: number
  dlq_pending: number
}

export interface DLQItem {
  id: string
  brand_id: string
  brand_name: string
  source: string
  hit_id: string
  error: string
  retry_count: number
  max_retries: number
  status: string
  created_at: string
}

export interface MonitorTriggerResult {
  total_hits_found: number
  total_hits_stored: number
  total_hits_enriched: number
}

export interface MonitorSingleTriggerResult {
  hits_found: number
  hits_stored: number
  hits_enriched: number
}
