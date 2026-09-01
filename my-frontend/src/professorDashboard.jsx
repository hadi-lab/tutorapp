import { useState, useEffect } from 'react'
import { Link , useNavigate} from 'react-router-dom'
function ProfessorDashboard(){
    const [courses,setCourses]=useState([])
    const [token,setToken]=useState("")
    const [courseTitle,setCoursetitle]=useState("")
    const [files,setFiles]=useState(null)
    const [fileInputKey, setFileInputKey] = useState(0)
    const navigate=useNavigate()

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
        catch(e){return}
        if(response.status===401){navigate("/login");return}
        const data=await response.json()
        setCourses([...courses,{course_id:data.course_id,title: courseTitle}])
        setCoursetitle("")
        setFiles(null)
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
        <div>
            <button onClick={logout} >logout.</button>
            
            <h3>Your share link:</h3>
            <p>{window.location.origin}/tutor/{token}</p>
            
            <button onClick={rotateToken} >Rotate Token?</button>

            <h3>Your courses:</h3>
            <ul>
                {courses.map(c =>(
                    <li key={c.course_id} >{c.title}
                    <button onClick={() => deleteCourse(c.course_id)} >Delete</button>
                    </li>
                ))}
            </ul>
            <h3>Add a course:</h3>
            <input value={courseTitle} onChange={(e) => setCoursetitle(e.target.value)} placeholder='course title' />
            <input key={fileInputKey} type="file" multiple onChange={(e)=> setFiles(e.target.files)}/>
            <button onClick={uploadCourse} >Upload course</button>


        </div>
    )


}
export default ProfessorDashboard