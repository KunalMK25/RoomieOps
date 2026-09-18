import { useState, useEffect } from 'react'
import { RoomieOpsApiClient } from '../api/client'
import './Chores.css'

interface Chore {
  chore_id: string
  title: string
  assigned_to: string
  status: 'pending' | 'completed'
  due_date: string
  frequency: string
  created_at: string
}

interface ChoresState {
  chores: Chore[]
  loading: boolean
  error: string | null
  filter: 'all' | 'my' | 'pending' | 'completed'
}

export function Chores() {
  const [state, setState] = useState<ChoresState>({
    chores: [],
    loading: true,
    error: null,
    filter: 'all',
  })

  const client = new RoomieOpsApiClient()
  const householdId = 'h_sunrise'
  const currentUserId = 'kunal' // TODO: from auth context

  useEffect(() => {
    loadChores()
  }, [])

  async function loadChores() {
    try {
      setState(s => ({ ...s, loading: true, error: null }))
      const response = await client.getChores(householdId).catch(() => ({ chores: [] }))
      setState(s => ({ ...s, chores: response.chores || [], loading: false }))
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to load chores',
        loading: false,
      }))
    }
  }

  async function toggleChoreStatus(choreId: string, currentStatus: string) {
    try {
      const newStatus = currentStatus === 'completed' ? 'pending' : 'completed'
      // TODO: Call backend to update chore status
      await loadChores()
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to update chore',
      }))
    }
  }

  if (state.loading) return <div className="chores"><p>Loading...</p></div>

  const filtered = state.chores.filter(chore => {
    if (state.filter === 'my') return chore.assigned_to === currentUserId
    if (state.filter === 'pending') return chore.status === 'pending'
    if (state.filter === 'completed') return chore.status === 'completed'
    return true
  })

  return (
    <div className="chores">
      <h2>Chores</h2>

      {state.error && <div className="error">{state.error}</div>}

      <div className="chores-controls">
        <button
          className={state.filter === 'all' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'all' }))}
        >
          All ({state.chores.length})
        </button>
        <button
          className={state.filter === 'my' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'my' }))}
        >
          My Chores ({state.chores.filter(c => c.assigned_to === currentUserId).length})
        </button>
        <button
          className={state.filter === 'pending' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'pending' }))}
        >
          Pending ({state.chores.filter(c => c.status === 'pending').length})
        </button>
        <button
          className={state.filter === 'completed' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'completed' }))}
        >
          Completed ({state.chores.filter(c => c.status === 'completed').length})
        </button>
      </div>

      <div className="chores-list">
        {filtered.length === 0 ? (
          <p className="empty">No chores</p>
        ) : (
          filtered.map(chore => (
            <div key={chore.chore_id} className={`chore-card ${chore.status}`}>
              <div className="chore-content">
                <h4>{chore.title}</h4>
                <p className="chore-meta">
                  Assigned to: <strong>{chore.assigned_to}</strong>
                </p>
                {chore.frequency && <p className="chore-frequency">{chore.frequency}</p>}
                {chore.due_date && (
                  <p className="chore-due">Due: {new Date(chore.due_date).toLocaleDateString()}</p>
                )}
              </div>
              <button
                className={`status-btn ${chore.status}`}
                onClick={() => toggleChoreStatus(chore.chore_id, chore.status)}
              >
                {chore.status === 'completed' ? '✓ Done' : 'Mark Done'}
              </button>
            </div>
          ))
        )}
      </div>

      <button onClick={loadChores} className="refresh-btn">Refresh</button>
    </div>
  )
}
