import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import UserDashboard from './pages/user-dashboard.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <UserDashboard />
  </StrictMode>,
)
