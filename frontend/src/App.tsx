import { useState } from 'react'
import './App.css'

function App() {
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
    <div className="app-container">
      <header>
        <h1>RoomieOps</h1>
        <nav>
          <a href="#dashboard">Dashboard</a>
          <a href="#copilot">Copilot</a>
          <a href="#money">Money</a>
          <a href="#chores">Chores</a>
          <a href="#maintenance">Maintenance</a>
          <a href="#shopping">Shopping</a>
          <a href="#household">Household</a>
        </nav>
      </header>
      <main>
        <section id="dashboard">
          <h2>Dashboard</h2>
          <p>Placeholder: Dashboard showing amounts owed, bills due, tasks due</p>
        </section>
        <section id="copilot">
          <h2>Ask RoomieOps</h2>
          <p>Placeholder: Copilot chat interface for household queries</p>
        </section>
      </main>
    </div>
  )
}

export default App
