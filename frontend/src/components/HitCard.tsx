import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Badge } from '@/components/ui/Badge'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { formatDateTime } from '@/utils/formatters'
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import type { Hit } from '@/types'

interface HitCardProps {
  hit: Hit
  onStatusChange?: (hitId: string, status: 'reviewed' | 'false_positive') => void
}

const severityColors: Record<string, 'danger' | 'warning' | 'info' | 'default'> = {
  CRITICAL: 'danger',
  HIGH: 'warning',
  MEDIUM: 'info',
  LOW: 'default',
}

const decisionColors: Record<string, 'danger' | 'purple' | 'success' | 'default'> = {
  ALERT: 'danger',
  ESCALATE: 'purple',
  SUPPRESS: 'success',
}

export function HitCard({ hit, onStatusChange }: HitCardProps) {
  const [expanded, setExpanded] = useState(false)

  const enrichment = hit.enrichment
  const evaluation = enrichment?.evaluation

  return (
    <motion.div layout>
      <Card
        className="cursor-pointer hover:border-border-glow transition-all"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-medium text-text-primary">{hit.brand_name}</span>
                <span className="text-text-muted">/</span>
                <span className="text-text-secondary text-sm">{hit.source}</span>
              </div>
              <p className="text-text-muted text-xs mt-0.5">{formatDateTime(hit.detected_at)}</p>
            </div>
          </div>

          <div className="flex items-center gap-2 ml-4">
            {evaluation?.severity && (
              <Badge variant={severityColors[evaluation.severity]}>
                {evaluation.severity}
              </Badge>
            )}
            {enrichment?.decision && (
              <Badge variant={decisionColors[enrichment.decision]}>
                {enrichment.decision}
              </Badge>
            )}
            <Badge
              variant={hit.processing_status === 'reviewed' ? 'success' : hit.processing_status === 'false_positive' ? 'default' : 'warning'}
              dot
            >
              {hit.processing_status}
            </Badge>
            {expanded ? <ChevronUp className="w-4 h-4 text-text-muted" /> : <ChevronDown className="w-4 h-4 text-text-muted" />}
          </div>
        </div>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="pt-4 mt-4 border-t border-border-subtle space-y-4">
                {hit.match_details?.matched_keywords?.length > 0 && (
                  <div>
                    <p className="text-sm text-text-muted mb-1">Matched Keywords</p>
                    <div className="flex flex-wrap gap-1.5">
                      {hit.match_details.matched_keywords.map((kw, i) => (
                        <Badge key={i} variant="info">{kw}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {evaluation?.reasoning && (
                  <div>
                    <p className="text-sm text-text-muted mb-1">LLM Reasoning</p>
                    <p className="text-sm text-text-secondary bg-white/5 rounded-lg p-3">
                      {evaluation.reasoning}
                    </p>
                  </div>
                )}

                {evaluation?.threat_types && evaluation.threat_types.length > 0 && (
                  <div>
                    <p className="text-sm text-text-muted mb-1">Threat Types</p>
                    <div className="flex flex-wrap gap-1.5">
                      {evaluation.threat_types.map((t, i) => (
                        <Badge key={i} variant="purple">{t}</Badge>
                      ))}
                    </div>
                  </div>
                )}

                {hit.source_url && (
                  <a
                    href={hit.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-sm text-cyan-neon hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="w-3 h-3" />
                    View Source
                  </a>
                )}

                <div>
                  <p className="text-sm text-text-muted mb-1">Content Preview</p>
                  <pre className="text-xs text-text-secondary bg-black/30 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap">
                    {hit.content_preview}
                  </pre>
                </div>

                {hit.processing_status === 'pending' && onStatusChange && (
                  <div className="flex gap-2 pt-2">
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        onStatusChange(hit.id, 'reviewed')
                      }}
                    >
                      Mark Reviewed
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={(e) => {
                        e.stopPropagation()
                        onStatusChange(hit.id, 'false_positive')
                      }}
                    >
                      False Positive
                    </Button>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    </motion.div>
  )
}
