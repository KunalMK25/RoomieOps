import { useState } from 'react'
import './App.css'
import Upload from './screens/Upload'
import Processing from './screens/Processing'
import Results from './screens/Results'

type Screen = 'upload' | 'processing' | 'results'

interface ProcessingState {
  documentId: string
  docType: string
  situation: string
}

function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('upload')
  const [processingState, setProcessingState] = useState<ProcessingState | null>(null)

  const handleUploadSubmit = (documentId: string, docType: string, situation: string) => {
    setProcessingState({ documentId, docType, situation })
    setCurrentScreen('processing')
  }

  const handleProcessingComplete = () => {
    setCurrentScreen('results')
  }

  const handleReset = () => {
    setCurrentScreen('upload')
    setProcessingState(null)
  }

  return (
    <div className="app">
      {currentScreen === 'upload' && (
        <Upload onSubmit={handleUploadSubmit} />
      )}
      {currentScreen === 'processing' && processingState && (
        <Processing 
          documentId={processingState.documentId}
          onComplete={handleProcessingComplete}
        />
      )}
      {currentScreen === 'results' && processingState && (
        <Results 
          documentId={processingState.documentId}
          onReset={handleReset}
        />
      )}
    </div>
  )
}

export default App
