import { useState } from 'react'
import './Results.css'
import { ProcessedDocument, Language, RiskTier } from '../types'

interface ResultsProps {
  result: ProcessedDocument
  onReset: () => void
}

export default function Results({ result, onReset }: ResultsProps) {
  const [expandedWhy, setExpandedWhy] = useState(false)
  const [language, setLanguage] = useState<Language>('en')

  if (!result.riskResult || !result.extractedClauses) {
    return (
      <div className="results-screen">
        <div className="results-container">
          <button onClick={onReset} className="button-back">
            ← Back
          </button>
          <p>Processing failed or incomplete.</p>
          <button onClick={onReset} className="button-secondary">
            Start Over
          </button>
        </div>
      </div>
    )
  }

  const riskResult = result.riskResult
  const sourceClause = result.extractedClauses.find((c) => c.clauseId === riskResult.clauseId)
  const explanation = result.explanations?.[language] || result.explanations?.['en'] || 'No explanation available'

  const riskLabels: Record<RiskTier, string> = {
    green: 'All Clear',
    yellow: 'Pay Attention',
    red: 'Potential Issue',
  }

  const riskEmojis: Record<RiskTier, string> = {
    green: '🟢',
    yellow: '🟡',
    red: '🔴',
  }

  const riskDescriptions: Record<RiskTier, string> = {
    green: 'No significant issue detected based on the available clauses.',
    yellow: 'A condition, exception, or requirement that you should check.',
    red: 'Your stated situation appears to conflict with a relevant requirement.',
  }

  return (
    <div className="results-screen">
      <div className="results-container">
        <button onClick={onReset} className="button-back">
          ← Back
        </button>

        <div className={`risk-card risk-${riskResult.riskTier}`}>
          <div className="risk-emoji">{riskEmojis[riskResult.riskTier]}</div>
          <div className="risk-label">{riskLabels[riskResult.riskTier]}</div>
          <p className="risk-description">{riskDescriptions[riskResult.riskTier]}</p>
        </div>

        <div className="explanation-box">
          <p>{explanation}</p>
        </div>

        <button
          onClick={() => setExpandedWhy(!expandedWhy)}
          className="button-why"
        >
          Why? {expandedWhy ? '▼' : '▶'}
        </button>

        {expandedWhy && (
          <div className="why-details">
            <div className="reasoning-section">
              <h4>Reasoning</h4>
              <p>{riskResult.reasoning}</p>
            </div>

            {sourceClause && (
              <div className="clause-section">
                <h4>Source Clause</h4>
                <div className="clause-box">
                  <div className="clause-section-ref">Section {sourceClause.section}</div>
                  <blockquote>{sourceClause.text}</blockquote>
                </div>
              </div>
            )}

            <div className="confidence-section">
              <h4>Confidence</h4>
              <p className="confidence-badge">
                {riskResult.confidence === 'high'
                  ? '✓ High'
                  : riskResult.confidence === 'medium'
                  ? '~ Medium'
                  : '⚠ Low'}
              </p>
              {riskResult.confidence === 'low' && (
                <p className="confidence-note">
                  This result requires manual verification. Please review the source clause carefully.
                </p>
              )}
            </div>
          </div>
        )}

        <div className="language-toggle">
          <label>Language:</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="language-select"
          >
            <option value="en">English</option>
            <option value="kn">ಕನ್ನಡ (Kannada)</option>
          </select>
        </div>

        <div className="disclaimer">
          <p>
            <strong>Disclaimer:</strong> Spashta provides source-grounded decision support and does
            not replace official institutional guidance.
          </p>
        </div>

        <button onClick={onReset} className="button-secondary">
          Analyze Another Document
        </button>
      </div>
    </div>
  )
}
