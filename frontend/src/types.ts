export interface EnrichedTicket {
  ticket_id: string
  last_event_id: string | null
  subject: string | null
  body: string | null
  channel: string | null
  priority: string | null
  customer_id: string | null
  status: string
  summary: string | null
  category: string | null
  sentiment: string | null
  risk: number | null
  suggested_reply: string | null
  created_at: string | null
  updated_at: string | null
}

export interface TicketListResponse {
  tickets: EnrichedTicket[]
  total: number
  page: number
  page_size: number
}

export interface AnalyticsSummary {
  total_tickets: number
  avg_risk: number
  high_risk_count: number
  by_category: Record<string, number>
  by_sentiment: Record<string, number>
}

export interface TicketFilters {
  category?: string
  sentiment?: string
  risk_min?: number
  risk_max?: number
  page: number
  page_size: number
  sort_by: string
  sort_order: 'asc' | 'desc'
}
