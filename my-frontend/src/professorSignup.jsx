import { useState } from 'react'
import { Link, useNavigate} from 'react-router-dom'
import "./auth.css"

function ProfessorSignup() {
  
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState("")
  const [result, setResult] = useState("")     
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)

  async function handleSubmit() {
    setLoading(true)
    let response;
    try {
      response = await fetch("/api/professor_signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, api_key: apiKey, model })
      })
    } catch (e) {
      setResult("Connection problem, please try again.")
      setLoading(false)
      return
    }

    const data = await response.json()
    if (response.status === 429) { setLoading(false); setResult("Slow down a moment — too many messages."); return }
    setLoading(false)
    if (data.redirect) {
      navigate(data.redirect)
    } else {
      setResult(data.error)     
    }
  }

  return (
    <div className="auth-container">
        <div className="auth-card">
            <h2 className="auth-heading">Professor Sign Up</h2>

            <input className="auth-field" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
            <input className="auth-field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
            <input className="auth-field" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" />
            <input className="auth-field" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="API Key" />


            <input className="auth-field" value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model (e.g. gpt-4o-mini)" />
            <p className="auth-hint">See LiteLLM's docs for model names by provider.</p>
            {result && <p className="auth-error">{result}</p>}

            <button className="auth-button" onClick={handleSubmit} disabled={loading}>
              {loading ? <span className="spinner" /> : "Sign up"}
              </button>

            <p className="auth-switch">
                Have an account?{" "}
                <span onClick={() => navigate("/login")}>Log in</span>
            </p>
        </div>
    </div>
)
}

export default ProfessorSignup