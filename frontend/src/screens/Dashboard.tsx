import { useState, useEffect } from 'react'
import { RoomieOpsApiClient } from '../api/client'
import './Dashboard.css'

interface DashboardState {
  balance: number
  recentExpenses: any[]
  choresDue: any[]
  maintenanceIssues: any[]
  shoppingItems: any[]
  loading: boolean
  error: string | null
}

export function Dashboard() {
  const [state, setState] = useState<DashboardState>({
    balance: 0,
    recentExpenses: [],
    choresDue: [],
    maintenanceIssues: [],
    shoppingItems: [],
    loading: true,
    error: null,
  })

  const client = new RoomieOpsApiClient()

  useEffect(() => {
    loadDashboard()
  }, [])

  async function loadDashboard() {
    try {
      setState(s => ({ ...s, loading: true, error: null }))
      
      // Get household ID from URL or session
      const householdId = 'h_sunrise' // TODO: get from session/context
      
      const [balances, expenses, chores, issues, shopping] = await Promise.all([
        client.getBalances(householdId).catch(() => ({ balance_paise: 0 })),
        client.getExpenses(householdId).catch(() => ({ expenses: [] })),
        client.getChores(householdId).catch(() => ({ chores: [] })),
        client.getMaintenanceIssues(householdId).catch(() => ({ issues: [] })),
        client.getShoppingItems(householdId).catch(() => ({ items: [] })),
      ])

      setState(s => ({
        ...s,
        balance: balances?.balance_paise || 0,
        recentExpenses: expenses?.expenses?.slice(0, 5) || [],
        choresDue: chores?.chores?.filter((c: any) => c.status === 'pending').slice(0, 3) || [],
        maintenanceIssues: issues?.issues?.filter((i: any) => i.status === 'open') || [],
        shoppingItems: shopping?.items || [],
        loading: false,
      }))
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to load dashboard',
        loading: false,
      }))
    }
  }

  if (state.loading) return <div className="dashboard"><p>Loading...</p></div>

  const balancePaise = state.balance
  const balanceRupees = (balancePaise / 100).toFixed(2)
  const balanceText = balancePaise > 0 ? `You are owed ₹${balanceRupees}` : balancePaise < 0 ? `You owe ₹${Math.abs(balancePaise / 100).toFixed(2)}` : 'Balanced'

  return (
    <div className="dashboard">
      <h2>Dashboard</h2>
      
      {state.error && <div className="error">{state.error}</div>}

      <section className="card balance-card">
        <h3>Your Balance</h3>
        <p className="balance-amount">{balanceText}</p>
        <button onClick={() => window.location.href = '#money'}>View Details</button>
      </section>

      <section className="card">
        <h3>Chores Due ({state.choresDue.length})</h3>
        {state.choresDue.length === 0 ? (
          <p className="empty">No chores assigned</p>
        ) : (
          <ul>
            {state.choresDue.map((chore: any) => (
              <li key={chore.chore_id}>{chore.title}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h3>Open Maintenance Issues ({state.maintenanceIssues.length})</h3>
        {state.maintenanceIssues.length === 0 ? (
          <p className="empty">No issues reported</p>
        ) : (
          <ul>
            {state.maintenanceIssues.map((issue: any) => (
              <li key={issue.issue_id}>
                {issue.title} <span className="location">({issue.location})</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h3>Shopping List ({state.shoppingItems.length})</h3>
        {state.shoppingItems.length === 0 ? (
          <p className="empty">Nothing to buy</p>
        ) : (
          <ul>
            {state.shoppingItems.map((item: any) => (
              <li key={item.item_id}>{item.item_name}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="card cta">
        <p>💬 Have a question about household finances or tasks?</p>
        <button onClick={() => window.location.href = '#copilot'} className="primary">Ask RoomieOps</button>
      </section>
    </div>
  )
}
