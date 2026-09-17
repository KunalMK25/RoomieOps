export type RiskTier = 'green' | 'yellow' | 'red'
export type Confidence = 'high' | 'medium' | 'low'
export type Language = 'en' | 'kn'

export interface Clause {
  clauseId: string
  text: string
  section: string
}

export interface Match {
  clauseId: string
  relevance: 'direct' | 'exception' | 'conditional'
  userFact: string
}

export interface RiskResult {
  riskTier: RiskTier
  clauseId: string
  reasoning: string
  confidence: Confidence
}

export interface ExplanationResult {
  explanation: string
  language: Language
}

export interface ProcessedDocument {
  documentId: string
  docType: string
  status: 'processing' | 'complete' | 'failed'
  extractedClauses?: Clause[]
  riskResult?: RiskResult
  explanations?: Record<Language, string>
  error?: string
  createdAt: string
}

export interface ApiResponse<T> {
  statusCode: number
  body: T
}
