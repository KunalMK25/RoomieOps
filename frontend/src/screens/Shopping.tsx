import { useState, useEffect } from 'react'
import { RoomieOpsApiClient } from '../api/client'
import './Shopping.css'

interface ShoppingItem {
  item_id: string
  name: string
  quantity?: number
  unit?: string
  category?: string
  purchased: boolean
  added_by: string
  added_at: string
  purchased_at?: string
}

interface ShoppingState {
  items: ShoppingItem[]
  loading: boolean
  error: string | null
  newItemName: string
  filter: 'all' | 'pending' | 'purchased'
}

export function Shopping() {
  const [state, setState] = useState<ShoppingState>({
    items: [],
    loading: true,
    error: null,
    newItemName: '',
    filter: 'pending',
  })

  const client = new RoomieOpsApiClient()
  const householdId = 'h_sunrise'
  const currentUserId = 'kunal' // TODO: from auth context

  useEffect(() => {
    loadItems()
  }, [])

  async function loadItems() {
    try {
      setState(s => ({ ...s, loading: true, error: null }))
      const response = await client.getShoppingItems(householdId).catch(() => ({ items: [] }))
      setState(s => ({ ...s, items: response.items || [], loading: false }))
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to load items',
        loading: false,
      }))
    }
  }

  async function addItem() {
    if (!state.newItemName.trim()) return

    try {
      await client.addShoppingItem(householdId, state.newItemName)
      setState(s => ({ ...s, newItemName: '' }))
      await loadItems()
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to add item',
      }))
    }
  }

  async function togglePurchased(itemId: string, currentPurchased: boolean) {
    try {
      // TODO: Call backend to update purchase status
      await loadItems()
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to update item',
      }))
    }
  }

  async function removeItem(itemId: string) {
    try {
      // TODO: Call backend to remove item
      await loadItems()
    } catch (error) {
      setState(s => ({
        ...s,
        error: error instanceof Error ? error.message : 'Failed to remove item',
      }))
    }
  }

  if (state.loading) return <div className="shopping"><p>Loading...</p></div>

  const filtered = state.items.filter(item => {
    if (state.filter === 'pending') return !item.purchased
    if (state.filter === 'purchased') return item.purchased
    return true
  })

  const pendingCount = state.items.filter(i => !i.purchased).length
  const purchasedCount = state.items.filter(i => i.purchased).length

  return (
    <div className="shopping">
      <h2>Shopping List</h2>

      {state.error && <div className="error">{state.error}</div>}

      <div className="shopping-form">
        <input
          type="text"
          placeholder="Add item..."
          value={state.newItemName}
          onChange={e => setState(s => ({ ...s, newItemName: e.target.value }))}
          onKeyDown={e => e.key === 'Enter' && addItem()}
        />
        <button onClick={addItem} className="add-btn">Add</button>
      </div>

      <div className="shopping-controls">
        <button
          className={state.filter === 'pending' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'pending' }))}
        >
          Pending ({pendingCount})
        </button>
        <button
          className={state.filter === 'purchased' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'purchased' }))}
        >
          Purchased ({purchasedCount})
        </button>
        <button
          className={state.filter === 'all' ? 'active' : ''}
          onClick={() => setState(s => ({ ...s, filter: 'all' }))}
        >
          All ({state.items.length})
        </button>
      </div>

      <div className="shopping-list">
        {filtered.length === 0 ? (
          <p className="empty">No items</p>
        ) : (
          filtered.map(item => (
            <div key={item.item_id} className={`shopping-item ${item.purchased ? 'purchased' : ''}`}>
              <div className="item-content">
                <input
                  type="checkbox"
                  checked={item.purchased}
                  onChange={() => togglePurchased(item.item_id, item.purchased)}
                  className="item-checkbox"
                />
                <div className="item-info">
                  <p className="item-name">{item.name}</p>
                  {item.quantity && item.unit && (
                    <p className="item-quantity">{item.quantity} {item.unit}</p>
                  )}
                  {item.category && <p className="item-category">{item.category}</p>}
                  <p className="item-added">Added by {item.added_by}</p>
                </div>
              </div>
              <button
                onClick={() => removeItem(item.item_id)}
                className="remove-btn"
                title="Remove item"
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>

      <button onClick={loadItems} className="refresh-btn">Refresh</button>
    </div>
  )
}
