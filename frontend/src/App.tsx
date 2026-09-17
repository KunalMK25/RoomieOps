import { useState } from 'react'
import './App.css'
import Upload from './screens/Upload'
import Processing from './screens/Processing'
import Results from './screens/Results'
import { ProcessedDocument, Language } from './types'

type Screen = 'upload' | 'processing' | 'results'

function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>('upload')
  const [processingState, setProcessingState] = useState<{
    documentId: string
    docType: string
    situation: string
    language: Language
    file?: File
  } | null>(null)
  const [result, setResult] = useState<ProcessedDocument | null>(null)

  const handleUploadSubmit = (
    documentId: string,
    docType: string,
    situation: string,
    language: Language,
    file: File
  ) => {
    setProcessingState({ documentId, docType, situation, language, file })
    setCurrentScreen('processing')
  }

  const handleProcessingComplete = (processedDoc: ProcessedDocument) => {
    setResult(processedDoc)
    setCurrentScreen('results')
  }

  const handleReset = () => {
    setCurrentScreen('upload')
    setProcessingState(null)
    setResult(null)
  }

  return (
    <div className="app">
      {currentScreen === 'upload' && (
        <Upload onSubmit={handleUploadSubmit} />
      )}
      {currentScreen === 'processing' && processingState && (
        <Processing 
          documentId={processingState.documentId}
          situation={processingState.situation}
          language={processingState.language}
          onComplete={handleProcessingComplete}
        />
      )}
      {currentScreen === 'results' && result && (
        <Results 
          result={result}
          onReset={handleReset}
        />
      )}
    </div>
  )
}

export default App
