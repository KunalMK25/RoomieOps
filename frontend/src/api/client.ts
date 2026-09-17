import { ProcessedDocument, Language } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000'

export const apiClient = {
  async getPresignedUrl(docType: string): Promise<{ documentId: string; uploadUrl: string }> {
    const response = await fetch(`${API_BASE_URL}/documents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('authToken') || ''}`,
      },
      body: JSON.stringify({ docType }),
    })

    if (!response.ok) {
      throw new Error(`Failed to get upload URL: ${response.statusText}`)
    }

    return response.json()
  },

  async startProcessing(
    documentId: string,
    situation: string,
    language: Language = 'en'
  ): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('authToken') || ''}`,
      },
      body: JSON.stringify({ situation, language }),
    })

    if (!response.ok) {
      throw new Error(`Failed to start processing: ${response.statusText}`)
    }

    return response.json()
  },

  async uploadDocument(
    presignedUrl: string,
    file: File
  ): Promise<void> {
    const response = await fetch(presignedUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': file.type,
      },
      body: file,
    })

    if (!response.ok) {
      throw new Error(`Failed to upload document: ${response.statusText}`)
    }
  },

  async getDocument(documentId: string): Promise<ProcessedDocument> {
    const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${localStorage.getItem('authToken') || ''}`,
      },
    })

    if (response.status === 404) {
      throw new Error('Document not found')
    }

    if (!response.ok) {
      throw new Error(`Failed to fetch document: ${response.statusText}`)
    }

    return response.json()
  },

  async pollDocument(
    documentId: string,
    maxAttempts: number = 60,
    intervalMs: number = 1000
  ): Promise<ProcessedDocument> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        const doc = await this.getDocument(documentId)
        if (doc.status === 'complete' || doc.status === 'failed') {
          return doc
        }
      } catch (error) {
        if (attempt === maxAttempts - 1) {
          throw error
        }
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs))
    }

    throw new Error('Processing timeout')
  },
}
