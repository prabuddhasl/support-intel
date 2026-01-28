import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './components/Dashboard'
import TicketDetail from './components/TicketDetail'
import Analytics from './components/Analytics'
import './styles/App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <aside className="sidebar">
          <div className="sidebar-brand">Support Intel</div>
          <nav className="sidebar-nav">
            <NavLink to="/" end>
              <span className="nav-icon">&#9776;</span> Dashboard
            </NavLink>
            <NavLink to="/analytics">
              <span className="nav-icon">&#9632;</span> Analytics
            </NavLink>
          </nav>
        </aside>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/tickets/:ticketId" element={<TicketDetail />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
