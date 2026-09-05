import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import "./dashboard.css"
import "./buttons.css"
function ProfessorDashboard(){
    const [courses,setCourses]=useState([])
    const [token,setToken]=useState("")
    const [courseTitle,setCoursetitle]=useState("")
    const [files,setFiles]=useState([])
    const [fileInputKey, setFileInputKey] = useState(0)
    const navigate=useNavigate()
    const [result,setResult]=useState("")

    function handleFileChange(e) {
    const picked = Array.from(e.target.files)
    setFiles(prev => [...prev, ...picked])      
    }

    useEffect(()=>{
        async function loadData(){
            let r1,r2
            try{
                [r1,r2]=await Promise.all([fetch("/api/professor_courses"),fetch("/api/show_prof_token")])

            }
            catch(e){
                return
            }
            if(r1.status===401 || r2.status===401){navigate("/login");return}
            const coursedata=await r1.json()
            const tokendata=await r2.json()
            setCourses(coursedata.courses)
            setToken(tokendata.token)

        }
        loadData()
    },[])


    async function uploadCourse() {
        const formdata=new FormData()
        formdata.append("course_title",courseTitle)
        for(let i =0;i<files.length;i++){
            formdata.append("files",files[i])
        }
        let response;
        try{
            response=await fetch("/api/ingest",{method:"POST",body:formdata})
        }
        catch(e){setResult("Upload failed, please try again.");return}
        if(response.status===401){navigate("/login");return}
        const data=await response.json()
        setCourses([...courses,{course_id:data.course_id,title: courseTitle}])
        setCoursetitle("")
        setFiles([])
        setFileInputKey(prev => prev + 1)

    }
    async function deleteCourse(course_id) {
        if(!confirm("Delete this course?This cannot be undone.")){
            return
        }
        let response
        try{
            response=await fetch("/api/delete_courses",{
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body:JSON.stringify({course_id})
            })
        }
        catch(e){
            return
        }
        if(response.status===401){navigate("/login");return}
        setCourses(courses.filter(c => c.course_id!==course_id ))
        
    }
    async function rotateToken() {
        if(!confirm("Rotate token? Your current link will stop working.")){return}
        let response;
        try{
            response=await fetch("/api/rotate_token",{method:"POST"})
        }
        catch(e){return}
        if(response.status===401){navigate("/login");return}
        const data=await response.json()
        setToken(data.new_token)
    }
    async function logout() {
        await fetch("/api/logout",{method:"POST"})
        navigate("/login")
    }
    return(
        <div className='dashboard-container'>

            <div className="dashboard-header">
                <h1 className="dashboard-title">Dashboard</h1>
                <button className="btn btn-secondary" onClick={logout}>Logout</button>
                <p>{result}</p>
            </div>
            <div className="dashboard-card">
                <h3>Your share link</h3>
                <p className="share-link">{window.location.origin}/tutor/{token}</p>
                <button className="btn btn-secondary" onClick={() => navigator.clipboard.writeText(`${window.location.origin}/tutor/${token}`)}>
                Copy
                </button>
                <button className="btn btn-secondary" onClick={rotateToken}>Rotate Token</button>
            </div>

            <div className='dasboard-card'>

                <h3>Your courses:</h3>
                <ul className='course-list'>
                    {courses.map(c =>(
                        <li className='course-item' key={c.course_id} ><span>{c.title}</span>
                        <button className="btn btn-danger" onClick={() => deleteCourse(c.course_id)} >Delete</button>
                        </li>
                    ))}
                </ul>
            </div>

            <div className="dashboard-card">
                <h3>Add a course</h3>
                <input className="auth-field" value={courseTitle} onChange={(e) => setCoursetitle(e.target.value)} placeholder="Course title" />
                <input key={fileInputKey} type="file" multiple onChange={handleFileChange} />

                {files.length > 0 && (
                <ul className="file-list">
                    {files.map((file, i) => (
                    <li key={i} className="file-item">
                    <span>{file.name}</span>
                    <button className="btn btn-danger" onClick={() => setFiles(prev => prev.filter((_, idx) => idx !== i))}>✕</button>
                    </li>
                    ))}
                </ul>
                )}
                <button className="btn btn-primary" onClick={uploadCourse}>Upload course</button>
            </div>


        </div>
    )


}
export default ProfessorDashboard