import { useState ,useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
function TutorPage(){
    const {token}=useParams()
    const navigate=useNavigate()


    const [courses, setCourses] = useState([])
    const [history, setHistory] = useState([])
    const [messages, setMessages] = useState([])
    const [question, setQuestion] = useState("")
    const [currentChatId, setCurrentChatId] = useState(null)
    const [currentCourseId, setCurrentCourseId] = useState(null)




    useEffect(()=>{
        async function LoadTutor() {
            const r1=await fetch("/api/tutor/"+token)
            if(r1.status===401){
                const d= await r1.json()
                navigate(d.redirect)
                return
            }
            const coursedata=await r1.json()
            setCourses(coursedata.courses)
            
            const r2 = await fetch("/api/my_chats")
            const historydata=await r2.json()
            setHistory(historydata.chats)
        }
        LoadTutor()
    },[])


    async function startChat(course_id){
        const response = await fetch("/api/pick_course", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ course_id })
        })
        if(response.status===401){navigate("/student_login");return}
        const data=await response.json()
        setCurrentChatId(data.chat_id)
        setCurrentCourseId(course_id)
        setMessages([])
    }

    async function OpenChat(chat_id,course_id) {
        setCurrentChatId(chat_id)
        setCurrentCourseId(course_id)
        const response=await fetch("/api/load_chat/"+ chat_id)
        if (response.status === 401) { navigate("/student_login"); return }
        if (response.status === 403) { setMessages([{ role: "error", content: "That chat isn't available." }]); return }
        const data = await response.json()
        setMessages(data.messages)
        
    }
    async function logout() {
        fetch("/api/logout",{method:"POST"})
        navigate("/student_login")
    }

        async function sendMessage() {
            if (!currentChatId) return
            const q = question
            setQuestion("")

            setMessages(prev => [...prev, { role: "user", content: q }])

            let response;
            try {
                response = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question: q, chat_id: currentChatId, course_id: currentCourseId })
                })
            } catch (e) {
                setMessages(prev => [...prev, { role: "error", content: "Connection problem." }])
                return
            }
            if (response.status === 401) { navigate("/student_login"); return }

            setMessages(prev => [...prev, { role: "assistant", content: "" }])

            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                const chunk = decoder.decode(value)
                setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1].content += chunk
                    return updated
                })
            }
        }   


    return(
        <div style={{display: "flex"}}>
            <div id='sidebar' >
                <h3>courses:</h3>
                <ul>
                    {courses.map(c=>(
                        <li key={c.course_id} >
                            <button onClick={()=> startChat(c.course_id)} >{c.title}</button>
                        </li>
                    ))}
                </ul>
                <h3>your past chats:</h3>
                <ul>
                    {history.map(c=>(
                        <li key={c.chat_id} >
                            <button onClick={()=>OpenChat(c.chat_id,c.course_id)} >{c.title} , {c.course_title}</button>
                        </li>
                    ))}
                </ul>
                <button onClick={logout} >Logout</button>

            </div>
            <div id='chat_area' >
                <div id='messages' >
                    {messages.map((c,i)=>(
                        <div key={i} className={c.role}>{c.content}</div>
                    ))}
                </div>
                <input value={question} onChange={(e)=> setQuestion(e.target.value)} placeholder='Ask a question...' />
                <button onClick={sendMessage} >Send</button>
            </div>

        </div>
    )
}
export default TutorPage