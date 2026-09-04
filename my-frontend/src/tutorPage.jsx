import { useState ,useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Send,Pencil, X } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import "./tutorPage.css";
function TutorPage(){
    const {token}=useParams()
    const navigate=useNavigate()
    const bottomRef = useRef(null)


    const [courses, setCourses] = useState([])
    const [history, setHistory] = useState([])
    const [messages, setMessages] = useState([])
    const [question, setQuestion] = useState("")
    const [currentChatId, setCurrentChatId] = useState(null)
    const [currentCourseId, setCurrentCourseId] = useState(null)
    const [error, setError] = useState(null)
    const textareaRef = useRef(null)
    const [loading, setLoading] = useState(false)
    const currentCourse = courses.find(c => c.course_id === currentCourseId)


    useEffect(() => {
        const el = textareaRef.current
        if (el) {
            el.style.height = "auto"
            el.style.height = el.scrollHeight + "px"
        }
    }, [question])

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

    useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages])


    async function deleteChat(chat_id) {
        if (!confirm("Delete this chat?")) return
        const response=await fetch("/api/delete_chat" ,{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({chat_id})
        })
        if(response.status===401){navigate("/student_login");return}
        if (response.status === 403) { showError("That chat isn't available."); return }
        setHistory(prev => prev.filter(c => c.chat_id !== chat_id))
        if (currentChatId === chat_id) {
            setMessages([])
            setCurrentChatId(null)
}
        
    }

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
        if (response.status === 403) { showError("That chat isn't available."); return }
        const data = await response.json()
        setMessages(data.messages)
        
    }
    async function logout() {
        fetch("/api/logout",{method:"POST"})
        navigate("/student_login")
    }

        async function sendMessage() {
            if (!question.trim()) return
            if (!currentChatId) return
            const q = question
            setQuestion("")

            setMessages(prev => [...prev, { role: "user", content: q }])
            setLoading(true)
            let response;
            try {
                response = await fetch("/api/chat", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ question: q, chat_id: currentChatId, course_id: currentCourseId })
                })
            } catch (e) {
                setMessages(prev => [...prev, { role: "error", content: "Connection problem." }])
                setLoading(false)
                return
            }
            if (response.status === 401) { setLoading(false);navigate("/student_login"); return }
            if (response.status === 429) { setLoading(false); showError("Slow down a moment — too many messages."); return }
            setMessages(prev => [...prev, { role: "assistant", content: "" }])

            const reader = response.body.getReader()
            const decoder = new TextDecoder()
            let firstChunk = true
            while (true) {
                const { done, value } = await reader.read()
                if (done) break
                if (firstChunk) {
                    setLoading(false)           
                    firstChunk = false
                }
                const chunk = decoder.decode(value)
                setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1].content += chunk
                    return updated
                })
            }
        }   
        async function renameChat(chat_id) {
            const title = prompt("New chat title:")
            if (!title) return

            const response = await fetch("/api/update_title", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ chat_id , title })
        })
            if (response.status === 401) { navigate("/student_login"); return }
            if (response.status === 400) { showError("Title too long — keep it under 30 characters."); return }
            if (response.status === 400) { showError("Access denied. Not ur chat."); return }
            
            setHistory(prev => prev.map(c =>
                c.chat_id === chat_id ? { ...c, title } : c
            ))
        }



        function showError(msg) {
            setError(msg)
            setTimeout(() => setError(null), 3000)
        }


    return(
        <div className='tutor-page'>
            {error && <div className="error-toast">{error}</div>}
            <div className='sidebar'  >
                <h3>courses:</h3>
                <ul className='courses'>
                    {courses.map(c=>(
                        <li className='course-element' key={c.course_id} >
                            <button onClick={()=> startChat(c.course_id)} >{c.title}</button>
                        </li>
                    ))}
                </ul>
                <h3>your past chats:</h3>
                <ul className='history'>
                    {history.map(c=>(
                        <li className='history-element' key={c.chat_id} >
                            <button
                                className={c.chat_id===currentChatId ? 'active':''}
                                onClick={()=>OpenChat(c.chat_id,c.course_id)} >
                                {c.title} , {c.course_title}
                            </button>
                            <button className="chat-action" onClick={() => renameChat(c.chat_id)}><Pencil size={16} /></button>
                            <button className="chat-action" onClick={() => deleteChat(c.chat_id)}><X size={16} /></button>
                        </li>
                    ))}
                </ul>
                <button className='logout-btn' onClick={logout} >Logout</button>

            </div>
            <div className='chat_area' >
                <div className='messages' >
                    {messages.length === 0 ? (
                        <div className="empty-state">
                            {currentChatId
                                ? `New chat started about ${currentCourse?.title} — ask your first question below!`
                                : "Pick a course to start chatting."}
                        </div>
                    ) : (
                        messages.map((c,i)=>(
                            <div key={i} className={c.role}>
                                <ReactMarkdown>
                                    {c.content}
                                </ReactMarkdown>
                            </div>
                        ))
                    )}
                    {loading && (
                        <div className="assistant typing">
                            <span></span><span></span><span></span>
                        </div>
                    )}
                <div ref={bottomRef} />
                </div>
                <div className='input-bar' >
                    <textarea
                    ref={textareaRef}
                    className="question"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault()
                            sendMessage()
                        }
                    }}
                    placeholder="Ask a question..."
                    rows={1}/>
                    <button onClick={sendMessage} disabled={!question.trim() || loading }><Send size={18} /></button>
                </div>
            </div>

        </div>
    )
}
export default TutorPage