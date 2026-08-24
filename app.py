from flask import Flask,request, Response, jsonify,render_template,session
import os
import sqlite3

from rag_pipeline import (
    init_db,
    save_messages,
    get_history,
    extract_pages,
    chunking,
    embedding,
    store_to_db,
    retrieve,
    create_conversation,
    answer,
    delete_course,
    get_professor_for_chat,
    ask,
    create_course,
    create_professor,
    create_student,
    get_professor_by_token,
    get_user_chats,
    rotate_token,
    get_professor_courses,
    validate_key,
    get_students_by_email,get_prof_by_email
)
from dotenv import load_dotenv

from werkzeug.security import check_password_hash,generate_password_hash
load_dotenv()

app=Flask(__name__)
app.secret_key=os.getenv("app_secret_key")
from rag_pipeline import embedder, collection, openai_key, db_path
k=8

from functools import wraps

def student_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "student_id" not in session:
            return jsonify({"error": "not logged in"}), 401
        return f(*args, **kwargs)
    return wrapper

def prof_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "prof_id" not in session:
            return jsonify({"error": "not logged in"}), 401
        return f(*args, **kwargs)
    return wrapper
def add_file_to_course(pdf, course_id, collection,file_id):
    pages = extract_pages(pdf)
    chunks = chunking(pages)
    embedded = embedding(chunks)
    store_to_db(embedded, collection, course_id,file_id)    
    return len(embedded)

def ingest_course_files(files,prof_id,collection,course_title):
    course_id=create_course(course_title,prof_id)
    os.makedirs(f"./uploads/{prof_id}", exist_ok=True)
    for file in files:
        file_id=os.path.splitext(file.filename)[0]
        path=f"./uploads/{prof_id}/{file.filename}"
        file.save(path)
        add_file_to_course(path,course_id,collection,file_id)
    return course_id


@app.route("/chat",methods=["POST"])
def ask_endpoint():
    question=request.json["question"]
    chat_id=request.json["chat_id"]
    course_id=request.json["course_id"]
    prof=get_professor_for_chat(chat_id)
    api_key = prof[0]      
    llm = prof[1] 
    def generate():
        full=""
        for piece in answer(question, k, chat_id, llm, collection, embedder, api_key, course_id):
            full+=piece
            yield piece
        
        save_messages(chat_id,"user",question)
        save_messages(chat_id,"assistant",full)
    return Response(generate(),mimetype="text/plain")

@app.route("/student_signup",methods=["POST"])
def student_route():
    data=request.json
    password=generate_password_hash(data["password"])
    id=create_student(data["email"],password)
    session["student_id"]=id
    return jsonify({"status":"successfully registered"})

@app.route("/student_login",methods=["POST"])
def s_login():
    data=request.json
    student=get_students_by_email(data["email"])
    if not student:
        return jsonify({"error": "no account with that email"}),401
    if not check_password_hash(student[1],data["password"]):
        return jsonify({"error":"wrong password"})
    session["student_id"]=student[0]
    return jsonify({"status":"logged in"})

@app.route("/professor_signup",methods=["POST"])
def professor_route():
    data=request.json
    if not validate_key(data["api_key"],data["model"]):
        return jsonify({"error":"invalid key or model"}),400
    password=generate_password_hash(data["password"])
    try:
        prof_id,token=create_professor(data["name"],data["email"],password,data["api_key"],data["model"])
    except sqlite3.IntegrityError:
        return jsonify({"error": "email already registered"}), 400
    session["prof_id"]=prof_id
    return jsonify({"professor_id": prof_id, "share_token": token})

@app.route("/prof_signup_render")
def sign_up_page():
    return render_template("prof_signup.html")



@app.route("/professor_login",methods=["POST"])
def p_login():
    data=request.json
    prof=get_prof_by_email(data["email"])
    if not  prof:
        return jsonify({"error": "no account with that email"}),401
    if not check_password_hash(prof[1],data["password"]):
        return jsonify({"error": "wrong password"}),401
    session["prof_id"]=prof[0]
    return jsonify({"status":"logged in"})

@app.route("/professor_courses",methods=["GET"])
@prof_required
def professor_courses():
    prof_id=session["prof_id"]
    course_rows=get_professor_courses(prof_id)
    course_list=[{"course_id":c[0],"course_title":c[1]} for c in course_rows]
    return jsonify({"courses":course_list})

@app.route("/delete_courses",methods=["POST"])
@prof_required
def delete_course_route():
    course_id=request.json["course_id"]
    prof_id=session["prof_id"]
    delete_course(course_id,prof_id)
    return jsonify({"status":"deleted"})


@app.route("/ingest",methods=["POST"])
@prof_required
def upload():
    prof_id=session["prof_id"]  
    course_title=request.form["course_title"]
    material=request.files.getlist("files")
    course_id=ingest_course_files(material,prof_id,collection,course_title)
    return jsonify({"course_id":course_id})

@app.route("/tutor/<token>",methods=["GET"])
def landing(token):
    prof=get_professor_by_token(token)
    if prof is None:
        return jsonify({"error": "invalid link"}), 404
    
    prof_id=prof[0]
    course_rows=get_professor_courses(prof_id)
    course_list=[{"course_id":c[0],"title":c[1]} for c in course_rows]
    return jsonify({"professor_id":prof_id,"courses":course_list})

@app.route("/create_convo",methods=["POST"])
@student_required
def create_convo():
    course_id=request.json["course_id"]
    student_id=session["student_id"]
    chat_id=create_conversation(student_id,course_id, "New chat")
    return jsonify({"chat_id":chat_id})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged out"})

init_db()
app.run(debug=True)