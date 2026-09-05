import "./auth.css"
import { useNavigate } from 'react-router-dom'



function Landing() {
    const navigate = useNavigate()
    return (
        <div className="auth-container">
            <div className="auth-card">
                <h2 className="auth-heading">Welcome</h2>
                <p className="auth-subtitle">How would you like to continue?</p>
                <button className="btn btn-primary" onClick={() => navigate("/login")}>
                    I'm a professor
                </button>
                <button className="btn btn-secondary" onClick={() => navigate("/student_login")}>
                    I'm a student
                </button>
            </div>
        </div>
    )
}
export default Landing
