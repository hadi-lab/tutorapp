import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import "./auth.css"
function StudentLogin(){
    const [email,setEmail]=useState("")
    const [password,setPassword]=useState("")
    const [result,setResult]=useState("")
    const navigate=useNavigate()
    const [loading, setLoading] = useState(false)


    async function handleStudentLogin(){
        setLoading(true)
        let response;
        try{
            response=await fetch("/api/student_login",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({email,password})
        })
        }
        catch(e){
            setResult("connection problem,please try again.")
            setLoading(false)
            return
        }
        const data=await response.json()
        if (response.status === 429) { setLoading(false); setResult("Slow down a moment — too many messages."); return }

        setLoading(false)
        if(data.redirect){
            navigate(data.redirect)
        }
        else{
            setResult(data.error)
        }
    }

    return(
        <div className="auth-container">
            <div className="auth-card">
                <h2 className="auth-heading">Student Login</h2>

                <input
                    className="auth-field"
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                />
                <input
                    className="auth-field"
                    type="password"
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                />
                {result && <p className="auth-error">{result}</p>} 
                <button className="auth-button" onClick={handleStudentLogin} disabled={loading}>
                    {loading ? <span className="spinner" /> : "Log in"}
                </button>

            <p className="auth-switch">
                Don't have an account?{" "}
                <span onClick={() => navigate("/student_signup")}>Sign up</span>
            </p>
            </div>
        </div>

    )
}
export default StudentLogin
