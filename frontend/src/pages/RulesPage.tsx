import React, { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from 'react-query'
import { rulesService, CacheRule } from '@/services/api-services'
import { Plus, Edit2, Trash2, Check, X } from 'lucide-react'

export const RulesPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [formData, setFormData] = useState({
    endpoint_pattern: '',
    ttl: 3600,
    enabled: true,
    cache_by_user: false,
    cache_by_query_params: false,
    cache_by_headers: false,
    max_cache_size: 1000,
    priority: 0,
    description: '',
  })

  const { data: rules, isLoading } = useQuery('cacheRules', () => rulesService.listRules())

  const createMutation = useMutation((data: Partial<CacheRule>) => rulesService.createRule(data), {
    onSuccess: () => {
      queryClient.invalidateQueries('cacheRules')
      resetForm()
    },
  })

  const updateMutation = useMutation(
    (data: Partial<CacheRule>) => rulesService.updateRule(editingId!, data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('cacheRules')
        resetForm()
      },
    }
  )

  const deleteMutation = useMutation((id: number) => rulesService.deleteRule(id), {
    onSuccess: () => {
      queryClient.invalidateQueries('cacheRules')
    },
  })

  const resetForm = () => {
    setFormData({
      endpoint_pattern: '',
      ttl: 3600,
      enabled: true,
      cache_by_user: false,
      cache_by_query_params: false,
      cache_by_headers: false,
      max_cache_size: 1000,
      priority: 0,
      description: '',
    })
    setShowForm(false)
    setEditingId(null)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (editingId) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-96">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">Cache Rules</h1>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-5 h-5" />
          New Rule
        </button>
      </div>

      {showForm && (
        <div className="card">
          <h2 className="text-xl font-bold mb-4">{editingId ? 'Edit Rule' : 'Create New Rule'}</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">
                  Endpoint Pattern
                </label>
                <input
                  type="text"
                  value={formData.endpoint_pattern}
                  onChange={(e) => setFormData({ ...formData, endpoint_pattern: e.target.value })}
                  placeholder="/api/users/*"
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">TTL (seconds)</label>
                <input
                  type="number"
                  value={formData.ttl}
                  onChange={(e) => setFormData({ ...formData, ttl: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={3}
              />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {[
                { key: 'enabled', label: 'Enabled' },
                { key: 'cache_by_user', label: 'Cache by User' },
                { key: 'cache_by_query_params', label: 'Cache by Query Params' },
                { key: 'cache_by_headers', label: 'Cache by Headers' },
              ].map(({ key, label }) => (
                <label key={key} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={formData[key as keyof typeof formData] as boolean}
                    onChange={(e) =>
                      setFormData({ ...formData, [key]: e.target.checked })
                    }
                    className="rounded"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>

            <div className="flex gap-2">
              <button type="submit" className="btn-primary">
                {editingId ? 'Update Rule' : 'Create Rule'}
              </button>
              <button type="button" onClick={resetForm} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Rules Table */}
      <div className="card overflow-x-auto">
        {rules && rules.length > 0 ? (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left font-semibold text-gray-700">Endpoint</th>
                <th className="px-4 py-2 text-center font-semibold text-gray-700">TTL</th>
                <th className="px-4 py-2 text-center font-semibold text-gray-700">Enabled</th>
                <th className="px-4 py-2 text-center font-semibold text-gray-700">Options</th>
                <th className="px-4 py-2 text-center font-semibold text-gray-700">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-mono text-blue-600 text-xs">{rule.endpoint_pattern}</td>
                  <td className="px-4 py-2 text-center">{rule.ttl}s</td>
                  <td className="px-4 py-2 text-center">
                    {rule.enabled ? (
                      <Check className="w-5 h-5 text-green-600 mx-auto" />
                    ) : (
                      <X className="w-5 h-5 text-red-600 mx-auto" />
                    )}
                  </td>
                  <td className="px-4 py-2 text-center">
                    <div className="flex gap-1 justify-center flex-wrap">
                      {rule.cache_by_user && <span className="badge badge-success text-xs">User</span>}
                      {rule.cache_by_query_params && <span className="badge badge-success text-xs">Params</span>}
                      {rule.cache_by_headers && <span className="badge badge-success text-xs">Headers</span>}
                    </div>
                  </td>
                  <td className="px-4 py-2 text-center flex gap-2 justify-center">
                    <button
                      onClick={() => {
                        setFormData(rule as any)
                        setEditingId(rule.id)
                        setShowForm(true)
                      }}
                      className="p-2 hover:bg-blue-100 rounded"
                    >
                      <Edit2 className="w-4 h-4 text-blue-600" />
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(rule.id)}
                      className="p-2 hover:bg-red-100 rounded"
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="text-center text-gray-500 py-8">No cache rules created yet</div>
        )}
      </div>
    </div>
  )
}
