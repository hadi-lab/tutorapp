import { Routes, Route } from 'react-router-dom'
import ProfessorSignup from './rofessorSignup'
import ProfLogin from './professorLogin'

function App() {
  return (
    <Routes>
      <Route path="/signup" element={<ProfessorSignup />} />
      <Route path="/login" element={<ProfLogin />} />
    </Routes>
  )
}

export default App