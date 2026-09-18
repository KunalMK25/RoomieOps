/**
 * RoomieOps Type Definitions
 * 
 * Core domain entities for shared-living operations
 */

// User/Member
export interface Member {
  memberId: string
  householdId: string
  name: string
  email: string
  room?: string
  isAdmin: boolean
  joinedAt: string
  absence?: {
    startDate: string
    endDate: string
  }
}

// Household
export interface Household {
  householdId: string
  name: string
  members: Member[]
  createdAt: string
  policy?: HouseholdPolicy
}

export interface HouseholdPolicy {
  householdId: string
  rules: string[]
  choreRotationDays?: number
  defaultSplitMethod?: 'equal' | 'per-person' | 'weighted'
}

// Expense
export interface Expense {
  expenseId: string
  householdId: string
  createdBy: string
  amount: number // in paise/cents for precision
  currency: string
  description: string
  category: 'bill' | 'grocery' | 'maintenance' | 'misc'
  splits: ExpenseSplit[]
  createdAt: string
  dueDate?: string
}

export interface ExpenseSplit {
  memberId: string
  amount: number // in paise/cents
  paid: boolean
  paidAt?: string
}

// Chore
export interface Chore {
  choreId: string
  householdId: string
  title: string
  description?: string
  frequency: 'daily' | 'weekly' | 'monthly' | 'once'
  rotation?: ChoreAssignment[]
  dueDate?: string
  completedBy?: string
  completedAt?: string
}

export interface ChoreAssignment {
  memberId: string
  assignedDate: string
  dueDate: string
  completed: boolean
}

// Maintenance Issue
export interface MaintenanceIssue {
  issueId: string
  householdId: string
  reportedBy: string
  title: string
  description: string
  severity: 'low' | 'medium' | 'high'
  status: 'open' | 'in-progress' | 'resolved'
  createdAt: string
  resolvedAt?: string
}

// Shopping Item
export interface ShoppingItem {
  itemId: string
  householdId: string
  name: string
  quantity: number
  unit: string
  purchased: boolean
  purchasedBy?: string
  purchasedAt?: string
}

// Notification/Event
export interface HouseholdEvent {
  eventId: string
  householdId: string
  type: 'bill_due' | 'chore_due' | 'payment_reminder' | 'maintenance_alert' | 'member_joined' | 'member_absent'
  title: string
  description: string
  data: Record<string, any>
  createdAt: string
  readBy?: string[]
}

// API Response
export interface ApiResponse<T> {
  status: 'success' | 'error'
  data?: T
  error?: {
    code: string
    message: string
  }
}

// Copilot Request/Response
export interface CopilotRequest {
  householdId: string
  memberId: string
  request: string
}

export interface CopilotResponse {
  status: 'success' | 'error'
  intent: string
  actions: CopilotAction[]
  explanation: string
}

export interface CopilotAction {
  type: string
  description: string
  params: Record<string, any>
}
