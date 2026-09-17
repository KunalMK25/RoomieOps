import { useState } from 'react'
import './Upload.css'
import { Language } from '../types'

interface UploadProps {
  onSubmit: (documentId: string, docType: string, situation: string, language: Language, file: File) => void
}

export default function Upload({ onSubmit }: UploadProps) {
  const [docType, setDocType] = useState('academic_regulation')
  const [situation, setSituation] = useState('')
  const [fileName, setFileName] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [language, setLanguage] = useState<Language>('en')

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      setFileName(selectedFile.name)
      setFile(selectedFile)
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!file || !situation.trim()) {
      alert('Please select a file and describe your situation')
      return
    }

    // Generate a document ID
    const documentId = `doc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    onSubmit(documentId, docType, situation, language, file)
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

        <div className="form-group">
          <label htmlFor="language">Explanation Language</label>
          <select
            id="language"
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="select"
          >
            <option value="en">English</option>
            <option value="kn">ಕನ್ನಡ (Kannada)</option>
          </select>
        </div>

        <button type="submit" className="button-primary">
          Analyze
        </button>
      </form>
    </div>
  )
}
