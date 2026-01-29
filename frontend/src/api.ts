import type {
  AnalyticsSummary,
  CitationChunk,
  EnrichedTicket,
  TicketFilters,
  TicketListResponse,
} from './types'

async function request<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as { detail?: string } | null
    throw new Error(err?.detail ?? `Request failed (${res.status})`)
  }
  const data = (await res.json()) as T
  return data
}

export async function fetchTickets(filters: TicketFilters): Promise<TicketListResponse> {
  const params = new URLSearchParams()
  params.set('page', String(filters.page))
  params.set('page_size', String(filters.page_size))
  params.set('sort_by', filters.sort_by)
  params.set('sort_order', filters.sort_order)
  if (filters.category) params.set('category', filters.category)
  if (filters.sentiment) params.set('sentiment', filters.sentiment)
  if (filters.risk_min !== undefined) params.set('risk_min', String(filters.risk_min))
  if (filters.risk_max !== undefined) params.set('risk_max', String(filters.risk_max))
  return request<TicketListResponse>(`/tickets?${params}`)
}

export async function fetchTicket(ticketId: string): Promise<EnrichedTicket> {
  return request<EnrichedTicket>(`/tickets/${encodeURIComponent(ticketId)}`)
}

export async function fetchAnalytics(): Promise<AnalyticsSummary> {
  return request<AnalyticsSummary>('/analytics/summary')
}

export async function fetchCitationChunk(chunkId: number): Promise<CitationChunk> {
  return request<CitationChunk>(`/kb/chunks/${chunkId}`)
}

export async function fetchCategories(): Promise<string[]> {
  return request<string[]>('/categories')
}

export async function fetchSentiments(): Promise<string[]> {
  return request<string[]>('/sentiments')
}
