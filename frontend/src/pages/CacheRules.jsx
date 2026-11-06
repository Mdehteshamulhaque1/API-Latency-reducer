import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  Plus,
  Pencil,
  Trash2,
  X,
  Zap,
  Clock,
  Flag,
  User,
  Hash,
  Braces,
  Loader2,
} from 'lucide-react'
import { useDashboardData } from '../context/DashboardDataContext'
import { apiClient } from '../lib/apiClient'
import { Card, PageHeader, Badge, LoadingBlock } from '../components/dashboard/ui'
import Button from '../components/Button'
import { formatMs } from '../lib/format'

const emptyRule = {
  endpoint_pattern: '/api/v1/',
  ttl: 300,
  enabled: true,
  cache_by_user: false,
  cache_by_query_params: true,
  cache_by_headers: false,
  max_cache_size: 1000,
  priority: 0,
  description: '',
}

function Modal({ open, onClose, title, children }) {
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-950/50 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.94, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.94, y: 20 }}
            transition={{ type: 'spring', stiffness: 320, damping: 28 }}
            className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-slate-100 px-6 py-4">
              <h3 className="font-display text-lg font-bold text-slate-900">{title}</h3>
              <button onClick={onClose} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600" aria-label="Close">
                <X size={18} />
              </button>
            </div>
            <div className="max-h-[70vh] overflow-y-auto scrollbar-thin px-6 py-5">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
        checked ? 'bg-gradient-to-r from-brand-500 to-violet-500' : 'bg-slate-200'
      }`}
      aria-pressed={checked}
      aria-label="Toggle"
    >
      <motion.span
        layout
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow ${checked ? 'left-[22px]' : 'left-0.5'}`}
      />
    </button>
  )
}

function RuleForm({ initial, onSubmit, onCancel }) {
  const [form, setForm] = useState(initial)
  const [saving, setSaving] = useState(false)
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await onSubmit(form)
    } finally {
      setSaving(false)
    }
  }

  const input =
    'w-full rounded-xl border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-sm outline-none transition-all focus:border-brand-500 focus:bg-white focus:ring-4 focus:ring-brand-500/10'

  return (
    <form onSubmit={submit} className="space-y-4">
      <div>
        <label className="mb-1.5 block text-xs font-semibold text-slate-700">Endpoint pattern</label>
        <input className={input} value={form.endpoint_pattern} onChange={(e) => set('endpoint_pattern', e.target.value)} required placeholder="/api/v1/analytics" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-slate-700">TTL (seconds)</label>
          <input type="number" min={0} className={input} value={form.ttl} onChange={(e) => set('ttl', Number(e.target.value))} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-semibold text-slate-700">Priority</label>
          <input type="number" min={0} className={input} value={form.priority} onChange={(e) => set('priority', Number(e.target.value))} />
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-semibold text-slate-700">Max cache size (KB)</label>
        <input type="number" min={100} className={input} value={form.max_cache_size} onChange={(e) => set('max_cache_size', Number(e.target.value))} />
      </div>

      <div className="space-y-2.5 rounded-xl border border-slate-100 bg-slate-50/60 p-4">
        {[
          { key: 'cache_by_user', label: 'Cache per user', icon: User },
          { key: 'cache_by_query_params', label: 'Include query params in key', icon: Hash },
          { key: 'cache_by_headers', label: 'Include Braces in key', icon: Braces },
        ].map((opt) => (
          <label key={opt.key} className="flex cursor-pointer items-center justify-between text-sm text-slate-700">
            <span className="inline-flex items-center gap-2">
              <opt.icon size={15} className="text-slate-400" />
              {opt.label}
            </span>
            <Toggle checked={form[opt.key]} onChange={(v) => set(opt.key, v)} />
          </label>
        ))}
      </div>

      <div>
        <label className="mb-1.5 block text-xs font-semibold text-slate-700">Description</label>
        <textarea rows={2} className={input} value={form.description || ''} onChange={(e) => set('description', e.target.value)} placeholder="Optional notes…" />
      </div>

      <div className="flex items-center justify-between gap-3 pt-2">
        <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-slate-700">
          Enabled
          <Toggle checked={form.enabled} onChange={(v) => set('enabled', v)} />
        </label>
        <div className="flex gap-3">
          <button type="button" onClick={onCancel} className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50">
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-brand-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-brand-600/25 transition-all hover:brightness-110 disabled:opacity-60"
          >
            {saving && <Loader2 size={15} className="animate-spin" />}
            Save rule
          </button>
        </div>
      </div>
    </form>
  )
}

export default function CacheRules() {
  const { rules, refresh } = useDashboardData()
  const [modal, setModal] = useState(null) // 'create' | rule object
  const [deleting, setDeleting] = useState(null)

  const handleCreate = async (rule) => {
    await apiClient.createRule(rule)
    setModal(null)
    refresh()
  }

  const handleUpdate = async (rule) => {
    const id = rule.id
    const payload = { ...rule }
    delete payload.id
    await apiClient.updateRule(id, payload)
    setModal(null)
    refresh()
  }

  const handleDelete = async (rule) => {
    await apiClient.deleteRule(rule.id)
    setDeleting(null)
    refresh()
  }

  return (
    <div>
      <PageHeader
        title="Cache rules"
        description="Define which endpoints get cached, for how long, and under what conditions."
        actions={
          <Button onClick={() => setModal('create')} icon={Plus}>
            New rule
          </Button>
        }
      />

      <Card pad={false}>
        {!rules ? (
          <LoadingBlock label="Loading cache rules…" />
        ) : rules.length === 0 ? (
          <div className="py-16 text-center">
            <Zap size={32} className="mx-auto text-slate-300" />
            <p className="mt-3 text-sm font-semibold text-slate-600">No cache rules yet</p>
            <p className="mt-1 text-xs text-slate-400">Create your first rule to start caching responses.</p>
          </div>
        ) : (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-[11px] uppercase tracking-widest text-slate-400">
                  <th className="px-6 py-4 font-semibold">Endpoint pattern</th>
                  <th className="px-4 py-4 font-semibold">TTL</th>
                  <th className="px-4 py-4 font-semibold">Priority</th>
                  <th className="px-4 py-4 font-semibold">Conditions</th>
                  <th className="px-4 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r) => (
                  <tr key={r.id} className="border-b border-slate-50 transition-colors last:border-0 hover:bg-slate-50/60">
                    <td className="px-6 py-4">
                      <p className="font-mono text-[13px] font-medium text-brand-700">{r.endpoint_pattern}</p>
                      {r.description && <p className="mt-0.5 max-w-[220px] truncate text-xs text-slate-400">{r.description}</p>}
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1.5 text-slate-600">
                        <Clock size={13} className="text-slate-400" />
                        {formatMs(r.ttl * 1000)}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center gap-1.5 text-slate-600">
                        <Flag size={13} className="text-slate-400" />
                        {r.priority}
                      </span>
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-1.5">
                        {r.cache_by_user && <Badge tone="brand"><User size={11} /> user</Badge>}
                        {r.cache_by_query_params && <Badge tone="slate"><Hash size={11} /> params</Badge>}
                        {r.cache_by_headers && <Badge tone="slate"><Braces size={11} /> Braces</Badge>}
                        {!r.cache_by_user && !r.cache_by_query_params && !r.cache_by_headers && (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <Badge tone={r.enabled ? 'green' : 'red'}>{r.enabled ? 'enabled' : 'disabled'}</Badge>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <Toggle checked={r.enabled} onChange={(v) => handleUpdate({ ...r, enabled: v })} />
                        <button
                          onClick={() => setModal(r)}
                          className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-brand-50 hover:text-brand-600"
                          aria-label="Edit rule"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          onClick={() => setDeleting(r)}
                          className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-rose-50 hover:text-rose-600"
                          aria-label="Delete rule"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={modal === 'create'} onClose={() => setModal(null)} title="Create cache rule">
        <RuleForm
          initial={emptyRule}
          onSubmit={handleCreate}
          onCancel={() => setModal(null)}
        />
      </Modal>

      <Modal open={Boolean(modal && modal !== 'create')} onClose={() => setModal(null)} title="Edit cache rule">
        {modal && modal !== 'create' && (
          <RuleForm
            initial={modal}
            onSubmit={handleUpdate}
            onCancel={() => setModal(null)}
          />
        )}
      </Modal>

      {/* Delete confirm */}
      <Modal open={Boolean(deleting)} onClose={() => setDeleting(null)} title="Delete cache rule">
        <p className="text-sm text-slate-600">
          Are you sure you want to delete the rule for{' '}
          <span className="font-mono font-bold text-brand-700">{deleting?.endpoint_pattern}</span>?
          This will stop caching for that endpoint and is not reversible.
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <button onClick={() => setDeleting(null)} className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50">
            Cancel
          </button>
          <button
            onClick={() => handleDelete(deleting)}
            className="rounded-xl bg-rose-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-rose-600/25 hover:bg-rose-700"
          >
            Delete rule
          </button>
        </div>
      </Modal>
    </div>
  )
}
