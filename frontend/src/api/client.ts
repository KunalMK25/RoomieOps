/**
 * RoomieOps API Client
 * 
 * Handles communication with backend Lambda functions for:
 * - Household operations
 * - Expense management
 * - Chore tracking
 * - Copilot requests
 * - Payment processing
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000'

interface ApiError {
  code: string
  message: string
}

interface ApiResponse<T> {
  status: 'success' | 'error'
  data?: T
  error?: ApiError
}

class RoomieOpsApiClient {
  private baseUrl: string
  private token: string | null = null

  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl
  }

  setToken(token: string) {
    this.token = token
  }

  private getAuthHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    const token = this.token || localStorage.getItem('authToken')
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    return headers
  }

  private async request<T>(
    method: string,
    path: string,
    body?: any
  ): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const response = await fetch(url, {
      method,
      headers: this.getAuthHeaders(),
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      const error = await response.json() as ApiError
      throw new Error(`${error.code}: ${error.message}`)
    }

    const data = await response.json()
    return data
  }

  // ===== Household Operations =====
  async getHouseholdState(householdId: string): Promise<any> {
    return this.request('POST', '/households', {
      operation: 'get_household_state',
      household_id: householdId,
    })
  }

  async getMembers(householdId: string): Promise<any> {
    return this.request('POST', '/households', {
      operation: 'get_members',
      household_id: householdId,
    })
  }

  async getHouseholdPolicy(householdId: string): Promise<any> {
    return this.request('POST', '/households', {
      operation: 'get_policy',
      household_id: householdId,
    })
  }

  // ===== Expense Management =====
  async createExpense(householdId: string, expenseData: any): Promise<any> {
    return this.request('POST', '/expenses', {
      operation: 'create',
      household_id: householdId,
      params: expenseData,
    })
  }

  async getExpenses(householdId: string): Promise<any> {
    return this.request('POST', '/expenses', {
      operation: 'list',
      household_id: householdId,
    })
  }

  async calculateSplit(householdId: string, expenseId: string, method: string): Promise<any> {
    return this.request('POST', '/expenses', {
      operation: 'calculate_split',
      household_id: householdId,
      params: { expense_id: expenseId, method },
    })
  }

  async getBalances(householdId: string): Promise<any> {
    return this.request('POST', '/expenses', {
      operation: 'get_balances',
      household_id: householdId,
    })
  }

  // ===== Chore Management =====
  async getChoreRotation(householdId: string): Promise<any> {
    return this.request('POST', '/chores', {
      operation: 'get_rotation',
      household_id: householdId,
    })
  }

  async createChore(householdId: string, choreData: any): Promise<any> {
    return this.request('POST', '/chores', {
      operation: 'create',
      household_id: householdId,
      params: choreData,
    })
  }

  async assignChore(householdId: string, choreId: string, memberId: string): Promise<any> {
    return this.request('POST', '/chores', {
      operation: 'assign',
      household_id: householdId,
      params: { chore_id: choreId, member_id: memberId },
    })
  }

  async completeChore(householdId: string, choreId: string): Promise<any> {
    return this.request('POST', '/chores', {
      operation: 'complete',
      household_id: householdId,
      params: { chore_id: choreId },
    })
  }

  async rebalanceChores(householdId: string): Promise<any> {
    return this.request('POST', '/chores', {
      operation: 'rebalance',
      household_id: householdId,
    })
  }

  // ===== Payment Processing =====
  async recordPayment(householdId: string, paymentData: any): Promise<any> {
    return this.request('POST', '/payments', {
      operation: 'record',
      household_id: householdId,
      params: paymentData,
    })
  }

  async getPaymentHistory(householdId: string): Promise<any> {
    return this.request('POST', '/payments', {
      operation: 'history',
      household_id: householdId,
    })
  }

  async simplifySettlement(householdId: string): Promise<any> {
    return this.request('POST', '/payments', {
      operation: 'simplify_settlement',
      household_id: householdId,
    })
  }

  // ===== Copilot (AI Agent) =====
  async sendCopilotRequest(
    householdId: string,
    memberId: string,
    request: string
  ): Promise<any> {
    return this.request('POST', '/copilot', {
      household_id: householdId,
      member_id: memberId,
      request,
    })
  }

  // ===== Notifications =====
  async getNotifications(householdId: string): Promise<any> {
    return this.request('POST', '/notifications', {
      household_id: householdId,
    })
  }
}

export const apiClient = new RoomieOpsApiClient()
