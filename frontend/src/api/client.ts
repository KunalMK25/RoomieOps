/**
 * RoomieOps API Client
 * 
 * Handles communication with backend Lambda functions
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000'

export class RoomieOpsApiClient {
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
      const error = await response.text()
      throw new Error(`API error: ${response.status} ${error}`)
    }

    return await response.json()
  }

  async getBalances(householdId: string): Promise<any> {
    return this.request('GET', `/households/${householdId}/balances`)
  }

  async getExpenses(householdId: string): Promise<any> {
    return this.request('GET', `/households/${householdId}/expenses`)
  }

  async getChores(householdId: string): Promise<any> {
    return this.request('GET', `/households/${householdId}/chores`)
  }

  async getMaintenanceIssues(householdId: string): Promise<any> {
    return this.request('GET', `/households/${householdId}/maintenance`)
  }

  async getShoppingItems(householdId: string): Promise<any> {
    return this.request('GET', `/households/${householdId}/shopping`)
  }

  async sendCopilotRequest(householdId: string, message: string): Promise<any> {
    return this.request('POST', `/households/${householdId}/copilot`, {
      message,
    })
  }

  async confirmAction(householdId: string, actionId: string, confirmed: boolean): Promise<any> {
    return this.request('POST', `/households/${householdId}/copilot/confirm`, {
      action_id: actionId,
      confirmed,
    })
  }

  async createExpense(householdId: string, expenseData: any): Promise<any> {
    return this.request('POST', `/households/${householdId}/expenses`, expenseData)
  }

  async createChore(householdId: string, choreData: any): Promise<any> {
    return this.request('POST', `/households/${householdId}/chores`, choreData)
  }

  async createMaintenanceIssue(householdId: string, issueData: any): Promise<any> {
    return this.request('POST', `/households/${householdId}/maintenance`, issueData)
  }

  async addShoppingItem(householdId: string, itemName: string): Promise<any> {
    return this.request('POST', `/households/${householdId}/shopping`, {
      item_name: itemName,
    })
  }

  async getMembers(householdId: string): Promise<any> {
    return this.request('GET', `/households/${householdId}/members`)
  }

  async getHouseholdState(householdId: string): Promise<any> {
    return this.request('GET', `/households/${householdId}`)
  }
}

export const apiClient = new RoomieOpsApiClient()
