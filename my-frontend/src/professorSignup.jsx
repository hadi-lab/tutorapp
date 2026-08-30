import { useState } from 'react'
import { Link } from 'react-router-dom'
function ProfessorSignup() {
  // one state per field
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState("")
  const [result, setResult] = useState("")     // for showing success/error messages

  async function handleSubmit() {
    let response;
    const navigate = useNavigate()
    try {
      response = await fetch("/api/professor_signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password, api_key: apiKey, model })
      })
    } catch (e) {
      setResult("Connection problem, please try again.")
      return
    }

    const data = await response.json()
    if (data.redirect) {
      navigate(data.redirect)
    } else {
      setResult(data.error)      // show the error
    }
  }

  return (
    <div>
      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" />
      <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="API Key" />
      <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model" />
      <button onClick={handleSubmit}>Sign up</button>
      <p>{result}</p>
      <p>Have an account? <Link to="/login">Log in</Link></p>
    </div>
  )
}

export default ProfessorSignup