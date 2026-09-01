import { useState } from 'react'
import { Link,useNavigate } from 'react-router-dom'
function ProfLogin(){
    const [email,setEmail]=useState("")
    const [password,setPassword]=useState("")
    const [Result,setResult]=useState("")
    const navigate = useNavigate()

    async function handleLogin() {
        let response;
        try{
            response=await fetch("/api/professor_login",{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({email,password})
            })
        }
        catch(e){
            setResult("Connection problem,please try again.")
            return
        }
        const data=await response.json()
        if(data.redirect){
            navigate(data.redirect)
        }
        else {
            setResult(data.error)
        }
        
    }
    return(
        <div>

        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder='email' />
        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder='password' />
        <button onClick={handleLogin} > login</button>
        <p>New here? <Link to="/signup">Sign up</Link></p>
        </div>

    )
}
export default ProfLogin