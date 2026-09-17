import { useEffect, useState } from 'react'
import './Processing.css'

interface ProcessingProps {
  documentId: string
  onComplete: () => void
}

type Stage = 'reading' | 'extracting' | 'matching' | 'classifying' | 'explaining'

export default function Processing({ documentId, onComplete }: ProcessingProps) {
  const [stage, setStage] = useState<Stage>('reading')
  const [progress, setProgress] = useState(0)

  const stages: { key: Stage; label: string }[] = [
    { key: 'reading', label: 'Reading document…' },
    { key: 'extracting', label: 'Extracting clauses…' },
    { key: 'matching', label: 'Matching your situation…' },
    { key: 'classifying', label: 'Classifying risk…' },
    { key: 'explaining', label: 'Preparing explanation…' },
  ]

  useEffect(() => {
    // Simulate processing stages
    const durations = [2000, 3000, 2500, 2000, 1500]
    let completed = 0

    const processStage = (index: number) => {
      if (index >= stages.length) {
        onComplete()
        return
      }

      setStage(stages[index].key)
      setProgress((index / stages.length) * 100)

      setTimeout(() => {
        completed++
        processStage(index + 1)
      }, durations[index])
    }

    processStage(0)
  }, [documentId, onComplete, stages.length])

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
