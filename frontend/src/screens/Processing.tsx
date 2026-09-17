import { useEffect, useState } from 'react'
import './Processing.css'
import { Language, ProcessedDocument } from '../types'
import { simulateProcessing } from '../api/mock'

interface ProcessingProps {
  documentId: string
  situation: string
  language: Language
  onComplete: (result: ProcessedDocument) => void
}

type Stage = 'reading' | 'extracting' | 'matching' | 'classifying' | 'explaining'

export default function Processing({ 
  documentId, 
  situation, 
  language,
  onComplete 
}: ProcessingProps) {
  const [stage, setStage] = useState<Stage>('reading')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const stages: { key: Stage; label: string }[] = [
    { key: 'reading', label: 'Reading document…' },
    { key: 'extracting', label: 'Extracting clauses…' },
    { key: 'matching', label: 'Matching your situation…' },
    { key: 'classifying', label: 'Classifying risk…' },
    { key: 'explaining', label: 'Preparing explanation…' },
  ]

  useEffect(() => {
    let isMounted = true

    const runProcessing = async () => {
      try {
        // Simulate processing stages with timing
        const durations = [2000, 3000, 2500, 2000, 1500]

        for (let index = 0; index < stages.length; index++) {
          if (!isMounted) return

          setStage(stages[index].key)
          setProgress((index / stages.length) * 100)
          await new Promise((resolve) => setTimeout(resolve, durations[index]))
        }

        if (!isMounted) return

        // After all stages complete, simulate backend processing
        const result = await simulateProcessing(documentId, situation, language)
        setProgress(100)
        
        if (isMounted) {
          onComplete(result)
        }
      } catch (err) {
        if (isMounted) {
          setError(err instanceof Error ? err.message : 'Processing failed')
        }
      }
    }

    runProcessing()

    return () => {
      isMounted = false
    }
  }, [documentId, situation, language, onComplete, stages.length])

  if (error) {
    return (
      <div className="processing-screen">
        <div className="processing-container">
          <h2>Processing Error</h2>
          <p className="stage-description" style={{ color: '#d32f2f' }}>
            {error}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="processing-screen">
      <div className="processing-container">
        <h2>Processing Your Document</h2>

        <div className="stages">
          {stages.map((s, index) => (
            <div
              key={s.key}
              className={`stage ${s.key === stage ? 'active' : ''} ${
                stages.findIndex((st) => st.key === stage) > index ? 'complete' : ''
              }`}
            >
              <div className="stage-dot">
                {stages.findIndex((st) => st.key === stage) > index ? '✓' : ''}
              </div>
              <div className="stage-label">{s.label}</div>
            </div>
          ))}
        </div>

        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>

        <p className="stage-description">
          {stages.find((s) => s.key === stage)?.label}
        </p>
      </div>
    </div>
  )
}
