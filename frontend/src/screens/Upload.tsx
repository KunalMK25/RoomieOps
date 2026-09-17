import { useState } from 'react'
import './Upload.css'

interface UploadProps {
  onSubmit: (documentId: string, docType: string, situation: string) => void
}

export default function Upload({ onSubmit }: UploadProps) {
  const [docType, setDocType] = useState('academic_regulation')
  const [situation, setSituation] = useState('')
  const [fileName, setFileName] = useState('')

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setFileName(file.name)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!fileName || !situation.trim()) {
      alert('Please select a file and describe your situation')
      return
    }

    // Generate a document ID
    const documentId = `doc-${Date.now()}`
    onSubmit(documentId, docType, situation)
  }

  return (
    <div className="upload-screen">
      <div className="header">
        <h1>Spashta</h1>
        <p className="tagline">Upload the rules. Tell us your situation. Know what they mean for you.</p>
      </div>

      <form onSubmit={handleSubmit} className="upload-form">
        <div className="form-group">
          <label htmlFor="file-input" className="file-label">
            <input
              id="file-input"
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={handleFileSelect}
              className="file-input"
            />
            <span className="file-button">
              {fileName ? `📄 ${fileName}` : '+ Upload Document'}
            </span>
          </label>
          <p className="file-help">PDF, JPG, or PNG</p>
        </div>

        <div className="form-group">
          <label htmlFor="doc-type">Document Type</label>
          <select
            id="doc-type"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="select"
          >
            <option value="academic_regulation">Academic Regulation</option>
            <option value="rental_agreement">Rental Agreement</option>
            <option value="utility_bill">Utility Bill</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="situation">Your Situation</label>
          <textarea
            id="situation"
            value={situation}
            onChange={(e) => setSituation(e.target.value)}
            placeholder="Example: I have 72% attendance and missed classes because of a medical reason."
            className="textarea"
            rows={4}
          />
        </div>

        <button type="submit" className="button-primary">
          Analyze
        </button>
      </form>
    </div>
  )
}
