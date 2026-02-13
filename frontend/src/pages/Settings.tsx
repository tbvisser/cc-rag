import { useState, useEffect } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { apiFetch } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface LLMConfig {
  model_name: string
  base_url: string
  api_key: string
}

interface EmbeddingConfig {
  model_name: string
  base_url: string
  api_key: string
  dimensions: number
}

interface RetrievalConfig {
  search_mode: string
  hybrid_alpha: number
  rerank_enabled: boolean
  rerank_api_key: string
  rerank_model: string
}

interface SettingsData {
  llm: LLMConfig
  embedding: EmbeddingConfig
  retrieval: RetrievalConfig
}

export default function Settings() {
  const { session } = useAuth()
  const token = session?.access_token

  const [llm, setLlm] = useState<LLMConfig>({ model_name: '', base_url: '', api_key: '' })
  const [embedding, setEmbedding] = useState<EmbeddingConfig>({ model_name: '', base_url: '', api_key: '', dimensions: 1536 })
  const [retrieval, setRetrieval] = useState<RetrievalConfig>({ search_mode: 'hybrid', hybrid_alpha: 0.5, rerank_enabled: false, rerank_api_key: '', rerank_model: 'rerank-v3.5' })
  const [showLlmKey, setShowLlmKey] = useState(false)
  const [showEmbeddingKey, setShowEmbeddingKey] = useState(false)
  const [showRerankKey, setShowRerankKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (!token) return
    apiFetch<SettingsData>('/api/settings', {}, token)
      .then((data) => {
        setLlm(data.llm)
        setEmbedding(data.embedding)
        if (data.retrieval) setRetrieval(data.retrieval)
      })
      .catch(() => {
        // Use defaults if settings endpoint fails
      })
      .finally(() => setLoading(false))
  }, [token])

  const handleSave = async () => {
    if (!token) return
    setSaving(true)
    setMessage(null)
    try {
      const data = await apiFetch<SettingsData>('/api/settings', {
        method: 'PUT',
        body: JSON.stringify({ llm, embedding, retrieval }),
      }, token)
      setLlm(data.llm)
      setEmbedding(data.embedding)
      if (data.retrieval) setRetrieval(data.retrieval)
      setMessage({ type: 'success', text: 'Settings saved successfully.' })
    } catch (err) {
      setMessage({ type: 'error', text: err instanceof Error ? err.message : 'Failed to save settings.' })
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (!token) return
    setLoading(true)
    apiFetch<SettingsData>('/api/settings', {}, token)
      .then((data) => {
        setLlm(data.llm)
        setEmbedding(data.embedding)
        if (data.retrieval) setRetrieval(data.retrieval)
        setMessage(null)
      })
      .finally(() => setLoading(false))
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading settings...</div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-lg p-6">
        <h1 className="text-2xl font-bold" style={{ fontFamily: 'Poppins, sans-serif' }}>Settings</h1>

        {message && (
          <div className={`mt-4 rounded-md p-3 text-sm ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-destructive/10 text-destructive'}`}>
            {message.text}
          </div>
        )}

        {/* LLM Configuration */}
        <section className="mt-8">
          <h2 className="text-base font-semibold">LLM Configuration</h2>
          <div className="mt-4 space-y-4">
            <Field label="Model Name" value={llm.model_name} onChange={(v) => setLlm({ ...llm, model_name: v })} placeholder="e.g. z-ai/glm-4.7" />
            <Field label="Base URL" value={llm.base_url} onChange={(v) => setLlm({ ...llm, base_url: v })} placeholder="https://openrouter.ai/api/v1" />
            <PasswordField label="API Key" value={llm.api_key} onChange={(v) => setLlm({ ...llm, api_key: v })} show={showLlmKey} onToggle={() => setShowLlmKey((p) => !p)} />
          </div>
        </section>

        <hr className="my-8" />

        {/* Embedding Configuration */}
        <section>
          <h2 className="text-base font-semibold">Embedding Configuration</h2>
          <div className="mt-4 space-y-4">
            <Field label="Model Name" value={embedding.model_name} onChange={(v) => setEmbedding({ ...embedding, model_name: v })} placeholder="e.g. text-embedding-ada-002" />
            <Field label="Base URL" value={embedding.base_url} onChange={(v) => setEmbedding({ ...embedding, base_url: v })} placeholder="https://api.openai.com/v1" />
            <PasswordField label="API Key" value={embedding.api_key} onChange={(v) => setEmbedding({ ...embedding, api_key: v })} show={showEmbeddingKey} onToggle={() => setShowEmbeddingKey((p) => !p)} />
            <Field label="Dimensions" value={String(embedding.dimensions)} onChange={(v) => setEmbedding({ ...embedding, dimensions: parseInt(v) || 0 })} placeholder="1536" type="number" />
          </div>
        </section>

        <hr className="my-8" />

        {/* Retrieval Configuration */}
        <section>
          <h2 className="text-base font-semibold">Retrieval Configuration</h2>
          <div className="mt-4 space-y-4">
            <div>
              <label className="block text-sm text-muted-foreground">Search Mode</label>
              <select
                value={retrieval.search_mode}
                onChange={(e) => setRetrieval({ ...retrieval, search_mode: e.target.value })}
                className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              >
                <option value="vector">Vector (Semantic)</option>
                <option value="keyword">Keyword (Full-Text)</option>
                <option value="hybrid">Hybrid (Vector + Keyword)</option>
              </select>
            </div>
            {retrieval.search_mode === 'hybrid' && (
              <div>
                <label className="block text-sm text-muted-foreground">
                  Alpha ({retrieval.hybrid_alpha.toFixed(2)}) — 0.0 = keyword only, 1.0 = vector only
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={retrieval.hybrid_alpha}
                  onChange={(e) => setRetrieval({ ...retrieval, hybrid_alpha: parseFloat(e.target.value) })}
                  className="mt-1 w-full"
                />
              </div>
            )}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="rerank-enabled"
                checked={retrieval.rerank_enabled}
                onChange={(e) => setRetrieval({ ...retrieval, rerank_enabled: e.target.checked })}
                className="h-4 w-4 rounded border-input"
              />
              <label htmlFor="rerank-enabled" className="text-sm text-muted-foreground">Enable Reranking (Cohere)</label>
            </div>
            {retrieval.rerank_enabled && (
              <>
                <PasswordField
                  label="Cohere API Key"
                  value={retrieval.rerank_api_key}
                  onChange={(v) => setRetrieval({ ...retrieval, rerank_api_key: v })}
                  show={showRerankKey}
                  onToggle={() => setShowRerankKey((p) => !p)}
                />
                <Field
                  label="Rerank Model"
                  value={retrieval.rerank_model}
                  onChange={(v) => setRetrieval({ ...retrieval, rerank_model: v })}
                  placeholder="rerank-v3.5"
                />
              </>
            )}
          </div>
        </section>

        {/* Actions */}
        <div className="mt-8 flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={handleCancel} disabled={saving}>Cancel</Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, value, onChange, placeholder, type = 'text' }: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  type?: string
}) {
  return (
    <div>
      <label className="block text-sm text-muted-foreground">{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
      />
    </div>
  )
}

function PasswordField({ label, value, onChange, show, onToggle }: {
  label: string
  value: string
  onChange: (v: string) => void
  show: boolean
  onToggle: () => void
}) {
  return (
    <div>
      <label className="block text-sm text-muted-foreground">{label}</label>
      <div className="relative mt-1">
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 pr-10 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  )
}
