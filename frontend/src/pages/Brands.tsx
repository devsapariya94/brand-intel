import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { BrandForm } from '@/components/BrandForm'
import { brandsApi } from '@/api/brands'
import { ChevronDown, ChevronUp, Search, Plus, Trash2, Edit, Power } from 'lucide-react'
import { toast } from 'sonner'
import type { Brand } from '@/types'

export default function Brands() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [activeOnly, setActiveOnly] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: brands, isLoading } = useQuery({
    queryKey: ['brands', activeOnly],
    queryFn: () => brandsApi.list(activeOnly),
  })

  const createMutation = useMutation({
    mutationFn: brandsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] })
      setShowForm(false)
      toast.success('Brand created successfully')
    },
    onError: () => toast.error('Failed to create brand'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Brand> }) => brandsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] })
      setEditingBrand(null)
      toast.success('Brand updated successfully')
    },
    onError: () => toast.error('Failed to update brand'),
  })

  const deleteMutation = useMutation({
    mutationFn: brandsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] })
      toast.success('Brand deleted')
    },
    onError: () => toast.error('Failed to delete brand'),
  })

  const toggleMutation = useMutation({
    mutationFn: brandsApi.toggle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] })
    },
  })

  const filtered = brands?.filter(
    (b) =>
      b.name.toLowerCase().includes(search.toLowerCase()) ||
      b.domain.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <PageLayout title="Brand Management">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 flex-1">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <Input
                placeholder="Search brands..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-text-secondary cursor-pointer">
              <input
                type="checkbox"
                checked={activeOnly}
                onChange={(e) => setActiveOnly(e.target.checked)}
                className="rounded border-border-subtle bg-white/5 text-cyan-neon focus:ring-cyan-neon/20"
              />
              Active only
            </label>
          </div>
          <Button onClick={() => setShowForm(true)}>
            <Plus className="w-4 h-4 mr-1.5" />
            Add Brand
          </Button>
        </div>

        {isLoading ? (
          <p className="text-text-muted">Loading brands...</p>
        ) : filtered?.length ? (
          <div className="space-y-3">
            {filtered.map((brand) => (
              <Card key={brand.id} className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-text-primary text-lg">{brand.name}</span>
                      <Badge variant={brand.active ? 'success' : 'danger'} dot>
                        {brand.active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <p className="text-text-secondary text-sm mt-0.5">{brand.domain}</p>
                  </div>

                  <div className="flex items-center gap-6 mr-4">
                    <div className="text-center">
                      <p className="text-2xl font-bold text-text-primary">{brand.stats?.total_hits ?? 0}</p>
                      <p className="text-xs text-text-muted">Total Hits</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-bold text-cyan-neon">{brand.stats?.hits_last_24h ?? 0}</p>
                      <p className="text-xs text-text-muted">24h</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => toggleMutation.mutate(brand.id)}
                    >
                      <Power className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setEditingBrand(brand)}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        if (confirm(`Delete ${brand.name}?`)) {
                          deleteMutation.mutate(brand.id)
                        }
                      }}
                    >
                      <Trash2 className="w-4 h-4 text-red-neon" />
                    </Button>
                    <button
                      onClick={() => setExpandedId(expandedId === brand.id ? null : brand.id)}
                      className="p-2 rounded-lg hover:bg-white/5 text-text-muted"
                    >
                      {expandedId === brand.id ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>

                {expandedId === brand.id && (
                  <div className="pt-4 border-t border-border-subtle grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-text-muted mb-1">Keywords</p>
                      <p className="text-text-secondary">{brand.keywords.join(', ') || 'None'}</p>
                    </div>
                    <div>
                      <p className="text-text-muted mb-1">Email Patterns</p>
                      <p className="text-text-secondary">{brand.email_patterns.join(', ') || 'None'}</p>
                    </div>
                    <div>
                      <p className="text-text-muted mb-1">Regex Patterns</p>
                      <p className="text-text-secondary">{brand.regex_patterns.join(', ') || 'None'}</p>
                    </div>
                    <div>
                      <p className="text-text-muted mb-1">Typosquat Variants</p>
                      <p className="text-text-secondary">{brand.typosquat_variants.join(', ') || 'None'}</p>
                    </div>
                    {brand.alert_email && (
                      <div>
                        <p className="text-text-muted mb-1">Alert Email</p>
                        <p className="text-text-secondary">{brand.alert_email}</p>
                      </div>
                    )}
                    {brand.slack_webhook && (
                      <div>
                        <p className="text-text-muted mb-1">Slack Webhook</p>
                        <p className="text-green-neon">Configured</p>
                      </div>
                    )}
                  </div>
                )}
              </Card>
            ))}
          </div>
        ) : (
          <p className="text-text-muted">No brands found</p>
        )}
      </div>

      <Modal open={showForm} onClose={() => setShowForm(false)} title="Add New Brand">
        <BrandForm
          onSubmit={(data) => createMutation.mutate(data)}
          loading={createMutation.isPending}
        />
      </Modal>

      <Modal
        open={!!editingBrand}
        onClose={() => setEditingBrand(null)}
        title={`Edit: ${editingBrand?.name}`}
      >
        {editingBrand && (
          <BrandForm
            brand={editingBrand}
            onSubmit={(data) => updateMutation.mutate({ id: editingBrand.id, data })}
            loading={updateMutation.isPending}
            submitLabel="Update Brand"
          />
        )}
      </Modal>
    </PageLayout>
  )
}
