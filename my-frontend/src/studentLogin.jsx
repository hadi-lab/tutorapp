import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
function StudentLogin(){
    const [email,setEmail]=useState("")
    const [password,setPassword]=useState("")
    const [result,setResult]=useState("")
    const navigate=useNavigate()


    async function handleStudentLogin(){
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
            return
        }
        const data=await response.json()
        if(data.redirect){
            navigate(data.redirect)
        }
        else{
            setResult(data.error)
        }
    }

    return(<div>
        <input value={email} onChange={(e) => setEmail(e.target.value) } placeholder='email'/>
        <input value={password} onChange={(e) => setPassword(e.target.value) } placeholder='password'/>
        <button onClick={handleStudentLogin} >Log in</button>
        <p>{result}</p>
        <p>New? <Link to="/student_signup">Signup</Link></p>
    </div>
    )
}
export default StudentLogin
