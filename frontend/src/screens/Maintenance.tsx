import { useState, useEffect } from 'react'
import { RoomieOpsApiClient } from '../api/client'
import './Maintenance.css'

interface MaintenanceIssue {
  issue_id: string
  title: string
  description: string
  room: string
  priority: 'low' | 'medium' | 'high'
  status: 'open' | 'in_progress' | 'resolved'
  reported_by: string
  assigned_to?: string
  created_at: string
  resolved_at?: string
}

interface MaintenanceState {
  issues: MaintenanceIssue[]
  loading: boolean
  error: string | null
  filter: 'all' | 'open' | 'in_progress' | 'resolved'
}

export function Maintenance() {
  const [state, setState] = useState<MaintenanceState>({
    issues: [],
    loading: true,
    error: null,
    filter: 'all',
  })

  const [expandedIssue, setExpandedIssue] = useState<string | null>(null)
  const client = new RoomieOpsApiClient()
  const householdId = 'h_sunrise'

  useEffect(() => {
    loadIssues()
  }, [])

  async function loadIssues() {
    try {
      setState(s => ({ ...s, loading: true, error: null }))
      const response = await client.getMaintenanceIssues(householdId).catch(() => ({ issues: [] }))
      setState(s => ({ ...s, issues: response.issues || [], loading: false }))
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to load issues',
        loading: false,
      }))
    }
  }

  async function updateIssueStatus(issueId: string, newStatus: string) {
    try {
      // TODO: Call backend to update issue status
      await loadIssues()
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to update issue',
      }))
    }
  }

  if (state.loading) return <div className="maintenance"><p>Loading...</p></div>

  const filtered = state.issues.filter(issue => {
    if (state.filter === 'all') return true
    return issue.status === state.filter
  })

  const openCount = state.issues.filter(i => i.status === 'open').length
  const inProgressCount = state.issues.filter(i => i.status === 'in_progress').length
  const resolvedCount = state.issues.filter(i => i.status === 'resolved').length

  const priorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return '#c00'
      case 'medium':
        return '#f70'
      case 'low':
        return '#080'
      default:
        return '#666'
    }
  }

  return (
    <div className="maintenance">
      <h2>Maintenance</h2>

      {state.error && <div className="error">{state.error}</div>}

      <div className="maintenance-controls">
        <button
          className={state.filter === 'all' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'all' }))}
        >
          All ({state.issues.length})
        </button>
        <button
          className={state.filter === 'open' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'open' }))}
        >
          Open ({openCount})
        </button>
        <button
          className={state.filter === 'in_progress' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'in_progress' }))}
        >
          In Progress ({inProgressCount})
        </button>
        <button
          className={state.filter === 'resolved' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'resolved' }))}
        >
          Resolved ({resolvedCount})
        </button>
      </div>

      <div className="issues-list">
        {filtered.length === 0 ? (
          <p className="empty">No issues</p>
        ) : (
          filtered.map(issue => (
            <div
              key={issue.issue_id}
              className={`issue-card ${issue.status}`}
              onClick={() => setExpandedIssue(expandedIssue === issue.issue_id ? null : issue.issue_id)}
            >
              <div className="issue-header">
                <div className="issue-title-group">
                  <span
                    className="priority-badge"
                    style={{ background: priorityColor(issue.priority) }}
                  >
                    {issue.priority.toUpperCase()}
                  </span>
                  <h4>{issue.title}</h4>
                </div>
                <span className="status-badge" data-status={issue.status}>
                  {issue.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>

              {expandedIssue === issue.issue_id && (
                <div className="issue-detail">
                  <p><strong>Room:</strong> {issue.room}</p>
                  <p><strong>Description:</strong> {issue.description}</p>
                  <p><strong>Reported by:</strong> {issue.reported_by}</p>
                  {issue.assigned_to && <p><strong>Assigned to:</strong> {issue.assigned_to}</p>}
                  <p><strong>Created:</strong> {new Date(issue.created_at).toLocaleDateString()}</p>
                  {issue.resolved_at && (
                    <p><strong>Resolved:</strong> {new Date(issue.resolved_at).toLocaleDateString()}</p>
                  )}

                  <div className="issue-actions">
                    {issue.status !== 'in_progress' && (
                      <button
                        className="action-btn"
                        onClick={e => {
                          e.stopPropagation()
                          updateIssueStatus(issue.issue_id, 'in_progress')
                        }}
                      >
                        Mark In Progress
                      </button>
                    )}
                    {issue.status !== 'resolved' && (
                      <button
                        className="action-btn resolve"
                        onClick={e => {
                          e.stopPropagation()
                          updateIssueStatus(issue.issue_id, 'resolved')
                        }}
                      >
                        Mark Resolved
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <button onClick={loadIssues} className="refresh-btn">Refresh</button>
    </div>
  )
}
