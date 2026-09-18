import { useState, useEffect } from 'react'
import { RoomieOpsApiClient } from '../api/client'
import './Money.css'

interface MoneyState {
  userBalance: number
  expenses: any[]
  members: any[]
  loading: boolean
  error: string | null
}

export function Money() {
  const [state, setState] = useState<MoneyState>({
    userBalance: 0,
    expenses: [],
    members: [],
    loading: true,
    error: null,
  })

  const [expandedExpense, setExpandedExpense] = useState<string | null>(null)
  const client = new RoomieOpsApiClient()
  const householdId = 'h_sunrise'

  useEffect(() => {
    loadMoney()
  }, [])

  async function loadMoney() {
    try {
      setState(s => ({ ...s, loading: true, error: null }))

      const [balances, expenses, members] = await Promise.all([
        client.getBalances(householdId).catch(() => ({})),
        client.getExpenses(householdId).catch(() => ({ expenses: [] })),
        client.getMembers(householdId).catch(() => ({ members: [] })),
      ])

      const userBalance = balances?.balance_paise || 0
      const expensesList = expenses?.expenses || []
      const membersList = members?.members || []

      setState(s => ({
        ...s,
        userBalance,
        expenses: expensesList,
        members: membersList,
        loading: false,
      }))
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to load data',
        loading: false,
      }))
    }
  }

  if (state.loading) return <div className="money"><p>Loading...</p></div>

  const balanceRupees = (state.userBalance / 100).toFixed(2)
  const balanceText = state.userBalance > 0 
    ? `You are owed ₹${balanceRupees}`
    : state.userBalance < 0
    ? `You owe ₹${Math.abs(state.userBalance / 100).toFixed(2)}`
    : 'Balanced'

  return (
    <div className="money">
      <h2>Money</h2>

      {state.error && <div className="error">{state.error}</div>}

      <section className="card balance-summary">
        <h3>Your Balance</h3>
        <p className="balance-text">{balanceText}</p>
        <p className="balance-detail">Based on {state.expenses.length} household expenses</p>
      </section>

      <section className="card">
        <h3>Recent Expenses</h3>
        {state.expenses.length === 0 ? (
          <p className="empty">No expenses yet</p>
        ) : (
          <div className="expense-list">
            {state.expenses.slice(0, 10).map((expense: any) => (
              <div key={expense.expense_id} className="expense-item">
                <div className="expense-header" onClick={() => setExpandedExpense(expandedExpense === expense.expense_id ? null : expense.expense_id)}>
                  <div>
                    <p className="expense-description">{expense.description || 'Expense'}</p>
                    <p className="expense-amount">₹{(expense.total_paise / 100).toFixed(2)}</p>
                  </div>
                  <p className="expense-date">{new Date(expense.created_at).toLocaleDateString()}</p>
                </div>
                {expandedExpense === expense.expense_id && (
                  <div className="expense-detail">
                    <p><strong>Payer:</strong> {expense.payer_id}</p>
                    <p><strong>Split Method:</strong> {expense.split_method}</p>
                    <p><strong>Participants:</strong></p>
                    <ul>
                      {expense.allocations?.map((alloc: any, idx: number) => (
                        <li key={idx}>{alloc.user_id}: ₹{(alloc.amount_paise / 100).toFixed(2)}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <h3>Member Balances</h3>
        {state.members.length === 0 ? (
          <p className="empty">No members</p>
        ) : (
          <table className="balances-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Balance</th>
              </tr>
            </thead>
            <tbody>
              {state.members.map((member: any) => {
                // TODO: fetch member balance from backend
                const balance = 0
                return (
                  <tr key={member.user_id}>
                    <td>{member.name}</td>
                    <td className={balance > 0 ? 'positive' : balance < 0 ? 'negative' : ''}>
                      {balance > 0 ? `Owed ₹${balance}` : balance < 0 ? `Owes ₹${Math.abs(balance)}` : 'Balanced'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </section>

      <button onClick={loadMoney} className="refresh-btn">Refresh</button>
    </div>
  )
}
