import { useState, useEffect } from 'react'
import { RoomieOpsApiClient } from '../api/client'
import './Household.css'

interface Member {
  user_id: string
  name: string
  email?: string
  role: 'admin' | 'member'
  joined_at: string
}

interface Room {
  room_id: string
  number: string
  beds: number
  members: string[]
}

interface HouseholdInfo {
  household_id: string
  name: string
  location?: string
  members: Member[]
  rooms: Room[]
  created_at: string
}

interface HouseholdState {
  household: HouseholdInfo | null
  loading: boolean
  error: string | null
  isAdmin: boolean
}

export function Household() {
  const [state, setState] = useState<HouseholdState>({
    household: null,
    loading: true,
    error: null,
    isAdmin: false,
  })

  const [expandedRoom, setExpandedRoom] = useState<string | null>(null)
  const client = new RoomieOpsApiClient()
  const householdId = 'h_sunrise'
  const currentUserId = 'kunal' // TODO: from auth context

  useEffect(() => {
    loadHousehold()
  }, [])

  async function loadHousehold() {
    try {
      setState(s => ({ ...s, loading: true, error: null }))
      const response = await client.getHouseholdState(householdId).catch(() => null)
      
      if (response) {
        const currentMember = response.members?.find((m: any) => m.user_id === currentUserId)
        const isAdmin = currentMember?.role === 'admin'
        
        setState(s => ({
          ...s,
          household: response,
          isAdmin,
          loading: false,
        }))
      } else {
        setState(s => ({
          ...s,
          error: 'Failed to load household',
          loading: false,
        }))
      }
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to load household',
        loading: false,
      }))
    }
  }

  if (state.loading) return <div className="household"><p>Loading...</p></div>
  if (!state.household) return <div className="household"><p className="error">{state.error || 'Household not found'}</p></div>

  const h = state.household

  return (
    <div className="household">
      <h2>Household</h2>

      <section className="card household-info">
        <h3>{h.name}</h3>
        {h.location && <p className="location">{h.location}</p>}
        <p className="created">Created {new Date(h.created_at).toLocaleDateString()}</p>
        {state.isAdmin && <span className="admin-badge">Admin</span>}
      </section>

      <section className="card">
        <h3>Members ({h.members.length})</h3>
        {h.members.length === 0 ? (
          <p className="empty">No members</p>
        ) : (
          <table className="members-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Joined</th>
              </tr>
            </thead>
            <tbody>
              {h.members.map(member => (
                <tr key={member.user_id} className={member.user_id === currentUserId ? 'current' : ''}>
                  <td>
                    <strong>{member.name}</strong>
                    {member.user_id === currentUserId && <span className="you-badge">(You)</span>}
                  </td>
                  <td>{member.email || '—'}</td>
                  <td>
                    <span className={`role-badge ${member.role}`}>
                      {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                    </span>
                  </td>
                  <td>{new Date(member.joined_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h3>Rooms ({h.rooms.length})</h3>
        {h.rooms.length === 0 ? (
          <p className="empty">No rooms</p>
        ) : (
          <div className="rooms-list">
            {h.rooms.map(room => (
              <div
                key={room.room_id}
                className="room-card"
                onClick={() => setExpandedRoom(expandedRoom === room.room_id ? null : room.room_id)}
              >
                <div className="room-header">
                  <h4>Room {room.number}</h4>
                  <span className="bed-count">{room.beds} bed{room.beds !== 1 ? 's' : ''}</span>
                </div>

                {expandedRoom === room.room_id && (
                  <div className="room-detail">
                    <p><strong>Members in room:</strong></p>
                    {room.members.length === 0 ? (
                      <p className="empty-inline">No members</p>
                    ) : (
                      <ul>
                        {room.members.map(memberId => {
                          const member = h.members.find(m => m.user_id === memberId)
                          return (
                            <li key={memberId}>
                              {member?.name || memberId}
                            </li>
                          )
                        })}
                      </ul>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {state.isAdmin && (
        <section className="card admin-actions">
          <h3>Admin Actions</h3>
          <p className="note">Additional admin features coming soon</p>
        </section>
      )}

      <button onClick={loadHousehold} className="refresh-btn">Refresh</button>
    </div>
  )
}
