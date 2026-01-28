import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchTicket } from '../api'
import type { EnrichedTicket } from '../types'

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString()
}

function riskColor(risk: number): string {
  if (risk > 0.7) return '#dc2626'
  if (risk > 0.3) return '#f59e0b'
  return '#16a34a'
}

function riskLabel(risk: number): string {
  if (risk > 0.7) return 'High'
  if (risk > 0.3) return 'Medium'
  return 'Low'
}

export default function TicketDetail() {
  const { ticketId } = useParams<{ ticketId: string }>()
  const [ticket, setTicket] = useState<EnrichedTicket | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!ticketId) return
    setLoading(true)
    fetchTicket(ticketId)
      .then(setTicket)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [ticketId])

  function copyReply() {
    if (!ticket?.suggested_reply) return
    navigator.clipboard.writeText(ticket.suggested_reply).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  if (loading) return <div className="detail-loading">Loading ticket...</div>
  if (error) return <div className="detail-error">{error}</div>
  if (!ticket) return <div className="detail-error">Ticket not found</div>

  const isPending = ticket.status === 'pending'

  return (
    <div className="ticket-detail">
      <Link to="/" className="back-link">&larr; Back to tickets</Link>

      <div className="detail-header">
        <div>
          <h1>{ticket.subject || 'Untitled'}</h1>
          <span className="detail-id">{ticket.ticket_id}</span>
        </div>
        <div className="detail-badges">
          <span className={`badge badge-status-${ticket.status}`}>
            {ticket.status.charAt(0).toUpperCase() + ticket.status.slice(1)}
          </span>
          {ticket.priority && (
            <span className={`badge badge-priority-${ticket.priority}`}>{ticket.priority}</span>
          )}
        </div>
      </div>

      <div className="detail-grid">
        <div className="detail-card">
          <h3>Ticket Info</h3>
          <dl>
            <dt>Channel</dt>
            <dd>{ticket.channel || '—'}</dd>
            <dt>Customer ID</dt>
            <dd>{ticket.customer_id || '—'}</dd>
            <dt>Created</dt>
            <dd>{formatDate(ticket.created_at)}</dd>
            <dt>Updated</dt>
            <dd>{formatDate(ticket.updated_at)}</dd>
          </dl>
        </div>

        <div className="detail-card detail-body-card">
          <h3>Description</h3>
          <p className="detail-body">{ticket.body || '—'}</p>
        </div>
      </div>

      {isPending ? (
        <div className="pending-banner">
          Enrichment in progress — AI analysis will appear here once complete.
        </div>
      ) : (
        <>
          <div className="enrichment-section">
            <h2>AI Analysis</h2>
            <div className="enrichment-grid">
              <div className="detail-card">
                <h3>Summary</h3>
                <p>{ticket.summary || '—'}</p>
              </div>

              <div className="detail-card">
                <h3>Classification</h3>
                <dl>
                  <dt>Category</dt>
                  <dd><span className="badge badge-category">{ticket.category || '—'}</span></dd>
                  <dt>Sentiment</dt>
                  <dd>
                    <span
                      className="badge"
                      style={{
                        color:
                          ticket.sentiment === 'negative' ? '#dc2626' :
                          ticket.sentiment === 'positive' ? '#16a34a' : '#6b7280',
                      }}
                    >
                      {ticket.sentiment || '—'}
                    </span>
                  </dd>
                </dl>
              </div>

              <div className="detail-card">
                <h3>Risk Score</h3>
                {ticket.risk !== null ? (
                  <div className="risk-display">
                    <span className="risk-value" style={{ color: riskColor(ticket.risk) }}>
                      {ticket.risk.toFixed(2)}
                    </span>
                    <span className="risk-label" style={{ color: riskColor(ticket.risk) }}>
                      {riskLabel(ticket.risk)}
                    </span>
                    <div className="risk-bar-bg">
                      <div
                        className="risk-bar-fill"
                        style={{
                          width: `${ticket.risk * 100}%`,
                          backgroundColor: riskColor(ticket.risk),
                        }}
                      />
                    </div>
                  </div>
                ) : (
                  <p>—</p>
                )}
              </div>
            </div>
          </div>

          {ticket.suggested_reply && (
            <div className="suggested-reply-card">
              <div className="reply-header">
                <h3>Suggested Reply</h3>
                <button className="copy-btn" onClick={copyReply}>
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
              <p className="reply-text">{ticket.suggested_reply}</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
