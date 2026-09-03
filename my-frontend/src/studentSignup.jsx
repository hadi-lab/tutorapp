import { useState } from 'react'
import "./auth.css"

import { Link, useNavigate } from 'react-router-dom'
function StudentSignup(){
    const [email,setEmail]=useState("")
    const [password,setPassword]=useState("")
    const [result,setResult]=useState("")
    const navigate=useNavigate()
    const [loading, setLoading] = useState(false)


    async function handleStudentSignup(){
        setLoading(true)
        let response;
        try{
            response=await fetch("/api/student_signup",{
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
                <h2 className="auth-heading">Student Signup</h2>

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
                <button className="auth-button" onClick={handleStudentSignup} disabled={loading}>
                    {loading ? <span className="spinner" /> : "Sign up"}
                </button>

            <p className="auth-switch">
                have an account?{" "}
                <span onClick={() => navigate("/student_login")}>log in</span>
            </p>
            </div>
        </div>

    )
}
export default StudentSignup

