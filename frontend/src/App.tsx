import { useState } from 'react'
import './App.css'
import { Dashboard } from './screens/Dashboard'
import { Copilot } from './screens/Copilot'

function App() {
  const [currentScreen, setCurrentScreen] = useState<string>('dashboard')
  const [authenticated, setAuthenticated] = useState(false)

  if (!authenticated) {
    return (
      <div className="app-container">
        <header>
          <h1>RoomieOps</h1>
          <p>AI-powered Shared-Living Operations Copilot</p>
        </header>
        <main>
          <button onClick={() => setAuthenticated(true)}>
            Sign In with Cognito
          </button>
        </main>
      </div>
    )
  }

  return (
    <div className="app-container authenticated">
      <header>
        <h1>RoomieOps</h1>
        <nav>
          <button 
            onClick={() => setCurrentScreen('dashboard')}
            className={currentScreen === 'dashboard' ? 'active' : ''}
          >
            Dashboard
          </button>
          <button 
            onClick={() => setCurrentScreen('copilot')}
            className={currentScreen === 'copilot' ? 'active' : ''}
          >
            Copilot
          </button>
          <button 
            onClick={() => setCurrentScreen('money')}
            className={currentScreen === 'money' ? 'active' : ''}
          >
            Money
          </button>
          <button 
            onClick={() => setCurrentScreen('chores')}
            className={currentScreen === 'chores' ? 'active' : ''}
          >
            Chores
          </button>
          <button 
            onClick={() => setCurrentScreen('maintenance')}
            className={currentScreen === 'maintenance' ? 'active' : ''}
          >
            Maintenance
          </button>
          <button 
            onClick={() => setCurrentScreen('shopping')}
            className={currentScreen === 'shopping' ? 'active' : ''}
          >
            Shopping
          </button>
        </nav>
      </header>
      <main>
        {currentScreen === 'dashboard' && <Dashboard />}
        {currentScreen === 'copilot' && <Copilot />}
        {currentScreen === 'money' && <div className="screen"><h2>Money (placeholder)</h2></div>}
        {currentScreen === 'chores' && <div className="screen"><h2>Chores (placeholder)</h2></div>}
        {currentScreen === 'maintenance' && <div className="screen"><h2>Maintenance (placeholder)</h2></div>}
        {currentScreen === 'shopping' && <div className="screen"><h2>Shopping (placeholder)</h2></div>}
      </main>
    </div>
  )
}

export default App
