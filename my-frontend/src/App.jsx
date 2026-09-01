import { Routes, Route } from 'react-router-dom'
import ProfessorSignup from './professorSignup'
import ProfLogin from './professorLogin'
import StudentLogin from './studentLogin'
import StudentSignup from './studentSignup'
import ProfessorDashboard from './professorDashboard'
import TutorPage from './tutorPage'
function App() {
  return (
    <Routes>
      <Route path="/signup" element={<ProfessorSignup />} />
      <Route path="/login" element={<ProfLogin />} />
      <Route path="/student_login" element={<StudentLogin />} />
      <Route path="/student_signup" element={<StudentSignup />} />
      <Route path="/professor_dashboard" element={<ProfessorDashboard />} />
      <Route path="/tutor/:token" element={<TutorPage />} />
    </Routes>
  )
}

export default App