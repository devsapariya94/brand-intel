import { useState } from 'react'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Button } from '@/components/ui/Button'
import { validateDomain, validateEmail, validateKeywords } from '@/utils/validators'
import type { Brand } from '@/types'

interface BrandFormProps {
  brand?: Brand
  onSubmit: (data: Partial<Brand>) => void
  loading?: boolean
  submitLabel?: string
}

export function BrandForm({ brand, onSubmit, loading, submitLabel = 'Create Brand' }: BrandFormProps) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [form, setForm] = useState({
    name: brand?.name ?? '',
    domain: brand?.domain ?? '',
    alert_email: brand?.alert_email ?? '',
    slack_webhook: brand?.slack_webhook ?? '',
    keywords: brand?.keywords.join(', ') ?? '',
    email_patterns: brand?.email_patterns.join(', ') ?? '',
    regex_patterns: brand?.regex_patterns.join('\n') ?? '',
    typosquat_variants: brand?.typosquat_variants.join(', ') ?? '',
    monitor_config: brand?.monitor_config ?? {
      github_enabled: true,
      hackernews_enabled: true,
      ransomware_enabled: true,
      xposedornot_enabled: true,
      intelx_enabled: true,
    },
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const newErrors: Record<string, string> = {}

    if (!form.name) newErrors.name = 'Brand name is required'
    if (!form.domain) newErrors.domain = 'Domain is required'
    else if (!validateDomain(form.domain)) newErrors.domain = 'Invalid domain format'
    if (form.alert_email && !validateEmail(form.alert_email)) newErrors.alert_email = 'Invalid email format'

    if (Object.keys(newErrors).length) {
      setErrors(newErrors)
      return
    }

    onSubmit({
      name: form.name,
      domain: form.domain,
      keywords: validateKeywords(form.keywords),
      email_patterns: validateKeywords(form.email_patterns),
      regex_patterns: form.regex_patterns.split('\n').filter(Boolean),
      typosquat_variants: validateKeywords(form.typosquat_variants),
      slack_webhook: form.slack_webhook || null,
      alert_email: form.alert_email || null,
      monitor_config: form.monitor_config,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Brand Name *"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          error={errors.name}
          placeholder="Acme Corp"
        />
        <Input
          label="Domain *"
          value={form.domain}
          onChange={(e) => setForm({ ...form, domain: e.target.value })}
          error={errors.domain}
          placeholder="acme.com"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Alert Email"
          value={form.alert_email}
          onChange={(e) => setForm({ ...form, alert_email: e.target.value })}
          error={errors.alert_email}
          placeholder="security@acme.com"
        />
        <Input
          label="Slack Webhook URL"
          value={form.slack_webhook}
          onChange={(e) => setForm({ ...form, slack_webhook: e.target.value })}
          placeholder="https://hooks.slack.com/..."
        />
      </div>

      <Textarea
        label="Keywords (comma-separated)"
        value={form.keywords}
        onChange={(e) => setForm({ ...form, keywords: e.target.value })}
        placeholder="acme, acme corp, acme inc"
        rows={2}
      />

      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="text-sm text-cyan-neon hover:underline"
      >
        {showAdvanced ? 'Hide' : 'Show'} Advanced Options
      </button>

      {showAdvanced && (
        <div className="space-y-4 p-4 rounded-lg bg-white/5 border border-border-subtle">
          <Textarea
            label="Email Patterns (comma-separated)"
            value={form.email_patterns}
            onChange={(e) => setForm({ ...form, email_patterns: e.target.value })}
            placeholder="@acme.com, @acmecorp.com"
            rows={2}
          />
          <Textarea
            label="Regex Patterns (one per line)"
            value={form.regex_patterns}
            onChange={(e) => setForm({ ...form, regex_patterns: e.target.value })}
            placeholder="pattern1\npattern2"
            rows={2}
          />
          <Textarea
            label="Typosquat Variants (comma-separated)"
            value={form.typosquat_variants}
            onChange={(e) => setForm({ ...form, typosquat_variants: e.target.value })}
            placeholder="acme.co, acm3.com"
            rows={2}
          />

          <div>
            <p className="text-sm font-medium text-text-secondary mb-2">Monitors</p>
            <div className="grid grid-cols-2 gap-2">
              {([
                ['github_enabled', 'GitHub'],
                ['hackernews_enabled', 'HackerNews'],
                ['ransomware_enabled', 'Ransomware'],
                ['xposedornot_enabled', 'XposedOrNot'],
                ['intelx_enabled', 'Intelligence X'],
              ] as const).map(([key, label]) => (
                <label key={key} className="flex items-center gap-2 text-sm text-text-secondary">
                  <input
                    type="checkbox"
                    checked={form.monitor_config[key]}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        monitor_config: { ...form.monitor_config, [key]: e.target.checked },
                      })
                    }
                    className="rounded border-border-subtle bg-white/5 text-cyan-neon focus:ring-cyan-neon/20"
                  />
                  {label}
                </label>
              ))}
            </div>
          </div>
        </div>
      )}

      <Button type="submit" loading={loading} className="w-full">
        {submitLabel}
      </Button>
    </form>
  )
}
