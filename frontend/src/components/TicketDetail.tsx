import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchCitationChunk, fetchTicket } from '../api'
import type { CitationChunk, EnrichedTicket } from '../types'

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
  const [openCitation, setOpenCitation] = useState<number | null>(null)
  const [citationDetails, setCitationDetails] = useState<Record<number, CitationChunk>>({})
  const [citationLoading, setCitationLoading] = useState<Record<number, boolean>>({})
  const [citationErrors, setCitationErrors] = useState<Record<number, string>>({})

  useEffect(() => {
    if (!ticketId) return
    setLoading(true)
    setOpenCitation(null)
    setCitationDetails({})
    setCitationLoading({})
    setCitationErrors({})
    fetchTicket(ticketId)
      .then(setTicket)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Request failed'),
      )
      .finally(() => setLoading(false))
  }, [ticketId])

  function copyReply() {
    if (!ticket?.suggested_reply) return
    void navigator.clipboard.writeText(ticket.suggested_reply).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  function toggleCitation(chunkId: number) {
    if (openCitation === chunkId) {
      setOpenCitation(null)
      return
    }
    setOpenCitation(chunkId)
    if (citationDetails[chunkId] || citationLoading[chunkId]) return
    setCitationLoading((prev) => ({ ...prev, [chunkId]: true }))
    setCitationErrors((prev) => ({ ...prev, [chunkId]: '' }))
    fetchCitationChunk(chunkId)
      .then((data) => {
        setCitationDetails((prev) => ({ ...prev, [chunkId]: data }))
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Failed to load source'
        setCitationErrors((prev) => ({ ...prev, [chunkId]: message }))
      })
      .finally(() => {
        setCitationLoading((prev) => ({ ...prev, [chunkId]: false }))
      })
  }

  if (loading) return <div className="detail-loading">Loading ticket...</div>
  if (error) return <div className="detail-error">{error}</div>
  if (!ticket) return <div className="detail-error">Ticket not found</div>

  const isPending = ticket.status === 'pending'
  const citations = ticket.citations ?? []

  return (
    <div className="ticket-detail">
      <Link to="/" className="back-link">&larr; Back to tickets</Link>

      <div className="detail-header">
        <div>
          <h1>{ticket.subject ?? 'Untitled'}</h1>
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
            <dd>{ticket.channel ?? '—'}</dd>
            <dt>Customer ID</dt>
            <dd>{ticket.customer_id ?? '—'}</dd>
            <dt>Created</dt>
            <dd>{formatDate(ticket.created_at)}</dd>
            <dt>Updated</dt>
            <dd>{formatDate(ticket.updated_at)}</dd>
          </dl>
        </div>

        <div className="detail-card detail-body-card">
          <h3>Description</h3>
          <p className="detail-body">{ticket.body ?? '—'}</p>
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
                <p>{ticket.summary ?? '—'}</p>
              </div>

              <div className="detail-card">
                <h3>Classification</h3>
                <dl>
                  <dt>Category</dt>
                  <dd><span className="badge badge-category">{ticket.category ?? '—'}</span></dd>
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
                      {ticket.sentiment ?? '—'}
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

          <div className="citations-card">
            <h3>Sources</h3>
            {citations.length === 0 ? (
              <p className="citations-empty">No citations available.</p>
            ) : (
              <ul className="citation-list">
                {citations.map((citation) => {
                  const isOpen = openCitation === citation.chunk_id
                  const details = citationDetails[citation.chunk_id]
                  const isLoading = citationLoading[citation.chunk_id]
                  const errorMessage = citationErrors[citation.chunk_id]

                  return (
                    <li key={citation.chunk_id} className="citation-item">
                      <div className="citation-header">
                        <div>
                          <div className="citation-title">
                            {citation.title}
                          </div>
                          <div className="citation-path">
                            {citation.heading_path || 'No section'}
                          </div>
                        </div>
                        <button
                          className="citation-toggle"
                          onClick={() => toggleCitation(citation.chunk_id)}
                        >
                          {isOpen ? 'Hide' : 'View'} snippet
                        </button>
                      </div>
                      {isOpen && (
                        <div className="citation-body">
                          {isLoading && <div className="citation-loading">Loading snippet...</div>}
                          {errorMessage && (
                            <div className="citation-error">{errorMessage}</div>
                          )}
                          {details && (
                            <>
                              <p className="citation-snippet">{details.content}</p>
                              <div className="citation-meta">
                                <span>
                                  {details.title || details.filename || 'Untitled document'}
                                </span>
                                {details.source_url && (
                                  <a
                                    className="citation-link"
                                    href={details.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                  >
                                    Open source
                                  </a>
                                )}
                              </div>
                            </>
                          )}
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  )
}
