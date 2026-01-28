import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchTickets, fetchCategories, fetchSentiments } from '../api'
import type { EnrichedTicket, TicketFilters } from '../types'

const RISK_PRESETS: { label: string; min?: number; max?: number }[] = [
  { label: 'All' },
  { label: 'High (>0.7)', min: 0.7 },
  { label: 'Medium (0.3–0.7)', min: 0.3, max: 0.7 },
  { label: 'Low (<0.3)', max: 0.3 },
]

const PAGE_SIZE = 15

function riskColor(risk: number | null): string {
  if (risk === null) return '#9ca3af'
  if (risk > 0.7) return '#dc2626'
  if (risk > 0.3) return '#f59e0b'
  return '#16a34a'
}

function sentimentColor(sentiment: string | null): string {
  if (sentiment === 'negative') return '#dc2626'
  if (sentiment === 'positive') return '#16a34a'
  return '#6b7280'
}

function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function Dashboard() {
  const navigate = useNavigate()

  const [tickets, setTickets] = useState<EnrichedTicket[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [categories, setCategories] = useState<string[]>([])
  const [sentimentOptions, setSentimentOptions] = useState<string[]>([])

  const [filters, setFilters] = useState<TicketFilters>({
    page: 1,
    page_size: PAGE_SIZE,
    sort_by: 'updated_at',
    sort_order: 'desc',
  })

  const [riskPreset, setRiskPreset] = useState(0)

  // Load filter options on mount
  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => undefined)
    fetchSentiments().then(setSentimentOptions).catch(() => undefined)
  }, [])

  // Load tickets whenever filters change
  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchTickets(filters)
      .then((data) => {
        setTickets(data.tickets)
        setTotal(data.total)
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Request failed'),
      )
      .finally(() => setLoading(false))
  }, [filters])

  function updateFilter(patch: Partial<TicketFilters>) {
    setFilters((prev) => ({ ...prev, page: 1, ...patch }))
  }

  function handleRiskPreset(index: number) {
    setRiskPreset(index)
    const preset = RISK_PRESETS[index]
    updateFilter({ risk_min: preset.min, risk_max: preset.max })
  }

  function handleSort(field: string) {
    setFilters((prev) => ({
      ...prev,
      sort_by: field,
      sort_order: prev.sort_by === field && prev.sort_order === 'asc' ? 'desc' : 'asc',
    }))
  }

  function sortIndicator(field: string) {
    if (filters.sort_by !== field) return ''
    return filters.sort_order === 'asc' ? ' \u25B2' : ' \u25BC'
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Tickets</h1>
        <span className="ticket-count">{total} total</span>
      </div>

      <div className="filter-bar">
        <div className="filter-group">
          <label>Category</label>
          <select
            value={filters.category ?? ''}
            onChange={(e) => updateFilter({ category: e.target.value || undefined })}
          >
            <option value="">All</option>
            {categories.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Sentiment</label>
          <select
            value={filters.sentiment ?? ''}
            onChange={(e) => updateFilter({ sentiment: e.target.value || undefined })}
          >
            <option value="">All</option>
            {sentimentOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div className="filter-group">
          <label>Risk</label>
          <select
            value={riskPreset}
            onChange={(e) => handleRiskPreset(Number(e.target.value))}
          >
            {RISK_PRESETS.map((p, i) => (
              <option key={i} value={i}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="dashboard-error">{error}</div>}

      <div className="table-wrap">
        <table className="ticket-table">
          <thead>
            <tr>
              <th className="sortable" onClick={() => handleSort('ticket_id')}>
                ID{sortIndicator('ticket_id')}
              </th>
              <th>Subject</th>
              <th>Category</th>
              <th>Sentiment</th>
              <th className="sortable" onClick={() => handleSort('risk')}>
                Risk{sortIndicator('risk')}
              </th>
              <th>Priority</th>
              <th>Status</th>
              <th className="sortable" onClick={() => handleSort('updated_at')}>
                Updated{sortIndicator('updated_at')}
              </th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={8} className="table-empty">Loading...</td></tr>
            ) : tickets.length === 0 ? (
              <tr><td colSpan={8} className="table-empty">No tickets found</td></tr>
            ) : (
              tickets.map((t) => (
                <tr
                  key={t.ticket_id}
                  className="ticket-row"
                  onClick={() => void navigate(`/tickets/${t.ticket_id}`)}
                >
                  <td className="cell-id">{t.ticket_id}</td>
                  <td className="cell-subject">{t.subject ?? '—'}</td>
                  <td><span className="badge badge-category">{t.category ?? '—'}</span></td>
                  <td>
                    <span className="badge" style={{ color: sentimentColor(t.sentiment) }}>
                      {t.sentiment ?? '—'}
                    </span>
                  </td>
                  <td>
                    <span className="risk-score" style={{ color: riskColor(t.risk) }}>
                      {t.risk !== null ? t.risk.toFixed(2) : '—'}
                    </span>
                  </td>
                  <td><span className={`badge badge-priority-${t.priority}`}>{t.priority ?? '—'}</span></td>
                  <td><span className={`badge badge-status-${t.status}`}>{statusLabel(t.status)}</span></td>
                  <td className="cell-date">{formatDate(t.updated_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          <button
            disabled={filters.page <= 1}
            onClick={() => setFilters((prev) => ({ ...prev, page: prev.page - 1 }))}
          >
            Previous
          </button>
          <span className="page-info">
            Page {filters.page} of {totalPages}
          </span>
          <button
            disabled={filters.page >= totalPages}
            onClick={() => setFilters((prev) => ({ ...prev, page: prev.page + 1 }))}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
