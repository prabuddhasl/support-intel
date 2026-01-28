import { useEffect, useState } from 'react'
import { fetchAnalytics } from '../api'
import type { AnalyticsSummary } from '../types'

function sentimentColor(s: string): string {
  if (s === 'negative') return '#dc2626'
  if (s === 'positive') return '#16a34a'
  return '#6b7280'
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAnalytics()
      .then(setData)
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : 'Request failed'),
      )
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="analytics-loading">Loading analytics...</div>
  if (error) return <div className="analytics-error">{error}</div>
  if (!data) return null

  const categoryMax = Math.max(...Object.values(data.by_category), 1)
  const sentimentMax = Math.max(...Object.values(data.by_sentiment), 1)

  return (
    <div className="analytics">
      <h1>Analytics</h1>

      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-value">{data.total_tickets}</span>
          <span className="stat-label">Total Tickets</span>
        </div>
        <div className="stat-card">
          <span className="stat-value" style={{ color: data.avg_risk > 0.7 ? '#dc2626' : data.avg_risk > 0.3 ? '#f59e0b' : '#16a34a' }}>
            {data.avg_risk.toFixed(2)}
          </span>
          <span className="stat-label">Avg Risk</span>
        </div>
        <div className="stat-card">
          <span className="stat-value" style={{ color: data.high_risk_count > 0 ? '#dc2626' : '#16a34a' }}>
            {data.high_risk_count}
          </span>
          <span className="stat-label">High Risk</span>
        </div>
      </div>

      <div className="breakdown-row">
        <div className="breakdown-card">
          <h2>By Category</h2>
          {Object.keys(data.by_category).length === 0 ? (
            <p className="no-data">No data yet</p>
          ) : (
            <ul className="bar-list">
              {Object.entries(data.by_category)
                .sort((a, b) => b[1] - a[1])
                .map(([cat, count]) => (
                  <li key={cat}>
                    <div className="bar-label">
                      <span>{cat}</span>
                      <span className="bar-count">{count}</span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill bar-fill-category"
                        style={{ width: `${(count / categoryMax) * 100}%` }}
                      />
                    </div>
                  </li>
                ))}
            </ul>
          )}
        </div>

        <div className="breakdown-card">
          <h2>By Sentiment</h2>
          {Object.keys(data.by_sentiment).length === 0 ? (
            <p className="no-data">No data yet</p>
          ) : (
            <ul className="bar-list">
              {Object.entries(data.by_sentiment)
                .sort((a, b) => b[1] - a[1])
                .map(([sent, count]) => (
                  <li key={sent}>
                    <div className="bar-label">
                      <span>{sent}</span>
                      <span className="bar-count">{count}</span>
                    </div>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${(count / sentimentMax) * 100}%`,
                          backgroundColor: sentimentColor(sent),
                        }}
                      />
                    </div>
                  </li>
                ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
