import { useState } from 'react'
import type { FormEvent } from 'react'

interface TicketForm {
  subject: string
  body: string
  channel: string
  priority: string
  customer_id: string
}

const CHANNELS = ['email', 'chat', 'phone']
const PRIORITIES = ['low', 'normal', 'high', 'critical']

export default function CreateTicket() {
  const [form, setForm] = useState<TicketForm>({
    subject: '',
    body: '',
    channel: 'email',
    priority: 'normal',
    customer_id: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null)

  function update(field: keyof TicketForm, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setResult(null)

    try {
      const payload: Record<string, string> = {
        subject: form.subject,
        body: form.body,
        channel: form.channel,
        priority: form.priority,
      }
      if (form.customer_id.trim()) {
        payload.customer_id = form.customer_id.trim()
      }

      const res = await fetch('/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        const err = (await res.json().catch(() => null)) as { detail?: string } | null
        throw new Error(err?.detail ?? `Request failed (${res.status})`)
      }

      const data = (await res.json()) as { ticket_id: string }
      setResult({ ok: true, message: `Ticket created: ${data.ticket_id}` })
      setForm({ subject: '', body: '', channel: 'email', priority: 'normal', customer_id: '' })
    } catch (err) {
      setResult({
        ok: false,
        message: err instanceof Error ? err.message : 'Something went wrong',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="create-ticket">
      <h1>Submit a Support Ticket</h1>
      <p className="subtitle">Describe your issue and we'll get back to you as soon as possible.</p>

      <form onSubmit={(e) => void handleSubmit(e)}>
        <div className="form-group">
          <label htmlFor="subject">Subject</label>
          <input
            id="subject"
            type="text"
            placeholder="Brief summary of your issue"
            value={form.subject}
            onChange={(e) => update('subject', e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="body">Description</label>
          <textarea
            id="body"
            placeholder="Please provide as much detail as possible..."
            rows={6}
            value={form.body}
            onChange={(e) => update('body', e.target.value)}
            required
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label htmlFor="channel">Channel</label>
            <select
              id="channel"
              value={form.channel}
              onChange={(e) => update('channel', e.target.value)}
            >
              {CHANNELS.map((ch) => (
                <option key={ch} value={ch}>
                  {ch.charAt(0).toUpperCase() + ch.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="priority">Priority</label>
            <select
              id="priority"
              value={form.priority}
              onChange={(e) => update('priority', e.target.value)}
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {p.charAt(0).toUpperCase() + p.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form-group">
          <label htmlFor="customer_id">Customer ID <span className="optional">(optional)</span></label>
          <input
            id="customer_id"
            type="text"
            placeholder="Your customer or account ID"
            value={form.customer_id}
            onChange={(e) => update('customer_id', e.target.value)}
          />
        </div>

        <button type="submit" className="submit-btn" disabled={submitting}>
          {submitting ? 'Submitting...' : 'Submit Ticket'}
        </button>
      </form>

      {result && (
        <div className={`result ${result.ok ? 'result-success' : 'result-error'}`}>
          {result.message}
        </div>
      )}
    </div>
  )
}
