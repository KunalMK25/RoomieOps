import { useState } from 'react'
import './Checklist.css'
import { ProcessedDocument, Language } from '../types'

interface ChecklistProps {
  documents: ProcessedDocument[]
  onReset: () => void
}

type DocumentStatus = 'complete' | 'incomplete' | 'irrelevant'

interface ChecklistItem {
  documentType: string
  requiredFor: string
  status: DocumentStatus
}

export default function Checklist({ documents, onReset }: ChecklistProps) {
  const [language, setLanguage] = useState<Language>('en')

  // Example readiness criteria for academic regulations
  const checklistTemplate: ChecklistItem[] = [
    {
      documentType: 'academic_regulation',
      requiredFor: 'Attendance requirements',
      status: documents.some((d) => d.docType === 'academic_regulation') ? 'complete' : 'incomplete',
    },
    {
      documentType: 'medical_certificate',
      requiredFor: 'Medical exemption eligibility',
      status: 'incomplete',
    },
    {
      documentType: 'exam_eligibility',
      requiredFor: 'Examination eligibility',
      status: documents.some((d) => d.docType === 'exam_eligibility') ? 'complete' : 'incomplete',
    },
    {
      documentType: 'supporting_document',
      requiredFor: 'Additional documentation',
      status: 'incomplete',
    },
  ]

  const completeness = checklistTemplate.filter((c) => c.status === 'complete').length
  const required = checklistTemplate.filter((c) => c.requiredFor.length > 0).length
  const percentComplete = Math.round((completeness / required) * 100)

  const labels = {
    en: {
      title: 'Readiness Checklist',
      description: 'Verify all required documents for your application',
      complete: '✓ Complete',
      incomplete: '✗ Incomplete',
      irrelevant: '— Not needed',
      progress: `${percentComplete}% Complete`,
      uploadMore: 'Upload More Documents',
      backToAnalysis: 'Back to Analysis',
    },
    kn: {
      title: 'ಸಿದ್ಧತೆ ಚೆಕ್‌ಲಿಸ್ಟ್',
      description: 'ನಿಮ್ಮ ಅರ್ಜಿಗೆ ಅಗತ್ಯವಿರುವ ಎಲ್ಲಾ ದಾಖಲೆಗಳನ್ನು ಪರಿಶೀಲಿಸಿ',
      complete: '✓ ಪೂರ್ಣ',
      incomplete: '✗ ಅಪೂರ್ಣ',
      irrelevant: '— ಅಗತ್ಯವಿಲ್ಲ',
      progress: `${percentComplete}% ಪೂರ್ಣ`,
      uploadMore: 'ಹೆಚ್ಚಿನ ದಾಖಲೆಗಳನ್ನು ಲೋಡ್ ಮಾಡಿ',
      backToAnalysis: 'ವಿಶ್ಲೇಷಣೆಗೆ ಹಿಂತಿರುಗಿ',
    },
  }

  const current = labels[language]

  return (
    <div className="checklist-screen">
      <div className="checklist-container">
        <button onClick={onReset} className="button-back">
          ← {current.backToAnalysis}
        </button>

        <div className="checklist-header">
          <h2>{current.title}</h2>
          <p>{current.description}</p>
        </div>

        <div className="progress-section">
          <div className="progress-bar-large">
            <div className="progress-fill-large" style={{ width: `${percentComplete}%` }} />
          </div>
          <p className="progress-text">{current.progress}</p>
        </div>

        <div className="checklist-items">
          {checklistTemplate.map((item, index) => (
            <div
              key={index}
              className={`checklist-item ${item.status}`}
            >
              <div className="item-status">
                {item.status === 'complete' && <span className="status-badge complete">✓</span>}
                {item.status === 'incomplete' && <span className="status-badge incomplete">✗</span>}
                {item.status === 'irrelevant' && <span className="status-badge irrelevant">—</span>}
              </div>
              <div className="item-content">
                <div className="item-type">{item.documentType}</div>
                <div className="item-required">{item.requiredFor}</div>
              </div>
              <div className="item-label">
                {item.status === 'complete' && current.complete}
                {item.status === 'incomplete' && current.incomplete}
                {item.status === 'irrelevant' && current.irrelevant}
              </div>
            </div>
          ))}
        </div>

        <div className="language-toggle-checklist">
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

        <button onClick={onReset} className="button-secondary">
          {current.uploadMore}
        </button>
      </div>
    </div>
  )
}
