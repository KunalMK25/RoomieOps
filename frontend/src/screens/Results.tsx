import { useState } from 'react'
import './Results.css'

interface ResultsProps {
  documentId: string
  onReset: () => void
}

type RiskTier = 'green' | 'yellow' | 'red'

interface Result {
  riskTier: RiskTier
  clauseId: string
  reasoning: string
  confidence: 'high' | 'medium' | 'low'
  explanation: string
  clause: {
    id: string
    text: string
    section: string
  }
}

export default function Results({ documentId, onReset }: ResultsProps) {
  const [expandedWhy, setExpandedWhy] = useState(false)
  const [language, setLanguage] = useState('en')

  // Mock result for demo
  const result: Result = {
    riskTier: 'red',
    clauseId: 'c1',
    reasoning: 'Stated attendance (72%) is below the 75% threshold in clause 4.2.',
    confidence: 'high',
    explanation:
      'Your attendance is currently below the required 75% threshold. You may be ineligible to write your exam unless you have documented medical exemption or successfully appeal for condonation.',
    clause: {
      id: 'c1',
      text: 'All students are required to maintain a minimum attendance of 75% in all courses across the academic session.',
      section: '4.1',
    },
  }

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

        <div className={`risk-card risk-${result.riskTier}`}>
          <div className="risk-emoji">{riskEmojis[result.riskTier]}</div>
          <div className="risk-label">{riskLabels[result.riskTier]}</div>
          <p className="risk-description">{riskDescriptions[result.riskTier]}</p>
        </div>

        <div className="explanation-box">
          <p>{result.explanation}</p>
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
              <p>{result.reasoning}</p>
            </div>

            <div className="clause-section">
              <h4>Source Clause</h4>
              <div className="clause-box">
                <div className="clause-section-ref">Section {result.clause.section}</div>
                <blockquote>{result.clause.text}</blockquote>
              </div>
            </div>

            <div className="confidence-section">
              <h4>Confidence</h4>
              <p className="confidence-badge">
                {result.confidence === 'high'
                  ? '✓ High'
                  : result.confidence === 'medium'
                  ? '~ Medium'
                  : '⚠ Low'}
              </p>
              {result.confidence === 'low' && (
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
            onChange={(e) => setLanguage(e.target.value)}
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
