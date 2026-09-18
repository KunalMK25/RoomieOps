import { useState, useRef, useEffect } from 'react'
import { RoomieOpsApiClient } from '../api/client'
import './Copilot.css'

interface Message {
  type: 'user' | 'assistant'
  content: string
  actionId?: string
  proposedAction?: any
  requiresConfirmation?: boolean
  status?: 'pending' | 'executing' | 'success' | 'error'
}

export function Copilot() {
  const [messages, setMessages] = useState<Message[]>([
    {
      type: 'assistant',
      content: 'Hi! I\'m RoomieOps. Ask me about balances, chores, expenses, maintenance, or shopping. What can I help with?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const client = new RoomieOpsApiClient()

  const householdId = 'h_sunrise' // TODO: get from session

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')

    // Add user message
    setMessages(m => [...m, { type: 'user', content: userMessage }])
    setLoading(true)

    try {
      const response = await client.sendCopilotRequest(householdId, userMessage)

      const assistantMessage: Message = {
        type: 'assistant',
        content: response.agent_response || response.message || 'Processing...',
        actionId: response.action_id,
        proposedAction: response.data,
        requiresConfirmation: response.requires_confirmation,
        status: response.status === 'success' ? 'success' : 'pending',
      }

      setMessages(m => [...m, assistantMessage])
    } catch (error) {
      setMessages(m => [
        ...m,
        {
          type: 'assistant',
          content: `Error: ${error instanceof Error ? error.message : 'Failed to process request'}`,
          status: 'error',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirm(actionId: string, confirmed: boolean) {
    setLoading(true)
    try {
      const result = await client.confirmAction(householdId, actionId, confirmed)

      setMessages(m => [
        ...m,
        {
          type: 'assistant',
          content: confirmed
            ? `✓ ${result.message || 'Action completed successfully'}`
            : `✗ ${result.message || 'Action cancelled'}`,
          status: confirmed ? 'success' : 'pending',
        },
      ])
    } catch (error) {
      setMessages(m => [
        ...m,
        {
          type: 'assistant',
          content: `Error: ${error instanceof Error ? error.message : 'Confirmation failed'}`,
          status: 'error',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="copilot-screen">
      <h2>Ask RoomieOps</h2>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type} ${msg.status || ''}`}>
            <div className="message-content">{msg.content}</div>

            {msg.requiresConfirmation && msg.actionId && (
              <div className="confirmation-box">
                <p className="confirmation-title">This action will update household state</p>
                {msg.proposedAction && (
                  <div className="proposal-details">
                    {JSON.stringify(msg.proposedAction, null, 2)
                      .split('\n')
                      .slice(0, 5)
                      .join('\n')}
                  </div>
                )}
                <div className="confirmation-buttons">
                  <button
                    className="confirm-btn"
                    onClick={() => handleConfirm(msg.actionId!, true)}
                    disabled={loading}
                  >
                    ✓ Confirm
                  </button>
                  <button
                    className="cancel-btn"
                    onClick={() => handleConfirm(msg.actionId!, false)}
                    disabled={loading}
                  >
                    ✗ Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about balances, chores, expenses..."
          disabled={loading}
          className="chat-input"
        />
        <button type="submit" disabled={loading || !input.trim()} className="send-btn">
          Send
        </button>
      </form>
    </div>
  )
}
