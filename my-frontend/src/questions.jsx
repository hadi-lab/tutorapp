import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import "./dashboard.css"
import "./buttons.css"


function CourseQuestions() {
    const { course_id } = useParams()
    const navigate = useNavigate()
    const [questions, setQuestions] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        async function load() {
            let response
            try {
                response = await fetch("/api/retrieve_questions", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ course_id })
                })
            } catch (e) {
                setLoading(false)
                return
            }
            if (response.status === 401) { navigate("/login"); return }
            if (response.status === 403) { navigate("/professor_dashboard"); return }
            const data = await response.json()
            setQuestions(data.questions)
            setLoading(false)
        }
        load()
    }, [course_id])

    return (
        <div className="dashboard-container">
            <button className="btn btn-secondary" onClick={() => navigate("/professor_dashboard")}>← Back</button>
            <h2>Student questions</h2>
            {loading ? (
                <p>Loading...</p>
            ) : questions.length === 0 ? (
                <p>No questions yet for this course.</p>
            ) : (
                <ul className="question-list">
                    {questions.map((q, i) => (
                        <li key={i}>
                            <span>{q[0]}</span>
                            <span className="question-time">{new Date(q[1]).toLocaleString()}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}
export default CourseQuestions