from flask import Flask,request, Response, jsonify,render_template,session,redirect,url_for
import os
import sqlite3
from cryptography.fernet import Fernet

def encrypt_key(plaintext):
    return fernet.encrypt(plaintext.encode()).decode()

def decrypt_key(ciphertext):
    return fernet.decrypt(ciphertext.encode()).decode()


app=Flask(__name__)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    get_remote_address,     
    app=app,
    default_limits=[]        
)


import rag_pipeline as rp
from rag_pipeline import embedder, collection, openai_key, db_path
from dotenv import load_dotenv

from werkzeug.security import check_password_hash,generate_password_hash
load_dotenv()

app.secret_key=os.getenv("app_secret_key")
fernet = Fernet(os.getenv("FERNET_KEY"))
k=8

from functools import wraps

def student_key():
    return str(session.get("student_id", get_remote_address()))



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
    pages = rp.extract_pages(pdf)
    chunks = rp.chunking(pages)
    embedded = rp.embedding(chunks)
    rp.store_to_db(embedded, collection, course_id,file_id)    
    return len(embedded)

def ingest_course_files(files,prof_id,collection,course_title):
    course_id=rp.create_course(course_title,prof_id)
    os.makedirs(f"./uploads/{prof_id}", exist_ok=True)
    for file in files:
        file_id=os.path.splitext(file.filename)[0]
        path=f"./uploads/{prof_id}/{file.filename}"
        file.save(path)
        add_file_to_course(path,course_id,collection,file_id)
    return course_id



@app.route("/api/chat",methods=["POST"])
@student_required
@limiter.limit("20 per minute", key_func=student_key)
def ask_endpoint():
    question=request.json["question"]
    chat_id=request.json["chat_id"]
    course_id=request.json["course_id"]
    history=rp.get_history(chat_id)
    if len(history) == 0:
        rp.insert_title(question[:40],chat_id)
    prof=rp.get_professor_for_chat(chat_id)
    api_key = decrypt_key(prof[0])      
    llm = prof[1] 
    def generate():
        full=""
        for piece in rp.answer(question, k, chat_id, llm, collection, embedder, api_key, course_id):
            full+=piece
            yield piece
        
        rp.save_messages(chat_id,"user",question)
        rp.save_messages(chat_id,"assistant",full)
    return Response(generate(),mimetype="text/plain")


@app.route("/api/my_chats")
@student_required
def get_chats():
    rows=rp.get_user_chats(session["student_id"])
    chats=[{"chat_id":c[0],"title":c[1],"course_id":c[2],"course_title":c[3]}for c in rows]
    return jsonify({"chats":chats})

@app.route("/api/pick_course",methods=["POST"])
@student_required
def pick_course():
    prof_id=session.get("current_prof_id")
    data=request.json
    if not rp.course_belongs_to_prof(data["course_id"],prof_id):
        return jsonify({"error": "invalid course"}), 403
    s_id=session["student_id"]
    chat_id=rp.create_conversation(s_id,data["course_id"])
    return jsonify({"chat_id":chat_id})


@app.route("/api/load_chat/<chat_id>",methods=["GET"])
@student_required
def load_chat(chat_id):
    if not rp.chat_belong_to_student(chat_id,session["student_id"]):
        return jsonify({"error":"not your chat"}),403
    rows=rp.get_history(chat_id)
    messages=[{"role":c[0],"content":c[1]} for c in rows]
    return jsonify({"messages":messages})


@app.route("/api/tutor/<token>",methods=["GET"])
def landing(token):
    if "student_id" not in session:
        session["pending_token"]=token
        return jsonify({"redirect":"/student_login"}),401
    prof=rp.get_professor_by_token(token)
    if prof is None:
        return jsonify({"error": "invalid link"}), 404
    
    prof_id=prof[0]
    session["current_prof_id"] = prof_id
    course_rows=rp.get_professor_courses(prof_id)
    course_list=[{"course_id":c[0],"title":c[1]} for c in course_rows]
    return jsonify({"courses":course_list})

@app.route("/api/student_signup",methods=["POST"])
@limiter.limit("5 per minute")
def student_route():
    if "pending_token" not in session:
        return jsonify({"error": "please use your professor's link to sign up"}), 400
    data=request.json
    password=generate_password_hash(data["password"])
    try:
        id=rp.create_student(data["email"],password)
    except sqlite3.IntegrityError:
        return jsonify({"error": "email already registered"}), 400
    session["student_id"]=id
    token=session.pop("pending_token")
    return jsonify({"redirect":"/tutor/" + token})


@app.route("/api/student_login",methods=["POST"])
@limiter.limit("5 per minute")
def s_login():
    
    data=request.json
    student=rp.get_students_by_email(data["email"])
    if not student:
        return jsonify({"error": "no account with that email"}),401
    if not check_password_hash(student[1],data["password"]):
        return jsonify({"error":"wrong password"}),401
    if "pending_token"not in session:
        return jsonify({"error": "please use your professor's link to log in"}), 400
    session["student_id"]=student[0]
    
    token=session.pop("pending_token")
    return jsonify({"redirect":"/tutor/" + token})
    






@app.route("/api/professor_signup",methods=["POST"])
@limiter.limit("5 per minute")
def professor_route():
    data=request.json
    if not rp.validate_key(data["api_key"],data["model"]):
        return jsonify({"error":"invalid key or model"}),400
    password=generate_password_hash(data["password"])
    encrypted = encrypt_key(data["api_key"])
    try:
        prof_id,token=rp.create_professor(data["name"],data["email"],password,encrypted,data["model"])
    except sqlite3.IntegrityError:
        return jsonify({"error": "email already registered"}), 400
    session["prof_id"]=prof_id
    return jsonify({"redirect":"/professor_dashboard"})



@app.route("/api/show_prof_token")
@prof_required
def show_prof_token():
    prof_id=session["prof_id"]
    prof_token=rp.get_token_by_prof_id(prof_id)
    return jsonify({"token":prof_token})

@app.route("/api/rotate_token", methods=["POST"])
@prof_required
def rotate_prof_token():
    new_token=rp.rotate_token(session["prof_id"])
    return jsonify({"new_token":new_token})

@app.route("/api/professor_login",methods=["POST"])
@limiter.limit("5 per minute")
def p_login():
    data=request.json
    prof=rp.get_prof_by_email(data["email"])
    if not  prof:
        return jsonify({"error": "no account with that email"}),401
    if not check_password_hash(prof[1],data["password"]):
        return jsonify({"error": "wrong password"}),401
    session["prof_id"]=prof[0]
    return jsonify({"redirect":"/professor_dashboard"}),200

@app.route("/api/professor_courses",methods=["GET"])
@prof_required
def professor_courses():
    prof_id=session["prof_id"]
    course_rows=rp.get_professor_courses(prof_id)
    course_list=[{"course_id":c[0],"title":c[1]} for c in course_rows]
    return jsonify({"courses":course_list})

@app.route("/api/delete_courses",methods=["POST"])
@prof_required
def delete_course_route():
    course_id=request.json["course_id"]
    prof_id=session["prof_id"]
    rp.delete_course(course_id,prof_id)
    return jsonify({"status":"deleted"}),200

@app.route("/api/delete_chat",methods=["POST"])
@student_required
def delete_chat():
    data=request.json
    s_id=session["student_id"]
    chat_id=data["chat_id"]

    if not rp.chat_belong_to_student(chat_id,s_id):
        return jsonify({"error":"not ur chat"}),403
    rp.delete_chat(s_id,chat_id)
    return jsonify({"status":"deleted"}),200


@app.route("/api/update_title",methods=["POST"])
@student_required
def update_title():
    data=request.json
    chat_id=data["chat_id"]
    title = data["title"].strip()

    if not rp.chat_belong_to_student(chat_id,session["student_id"]):
            return jsonify({"error":"not ur chat"}),403
    if not title.strip(): return jsonify({"error": "empty title"})
    if len(title) > 30:
        return jsonify({"error": "title too long"}), 400
    rp.insert_title(title,chat_id)
    return jsonify({"status":"success"})

@app.route("/api/ingest",methods=["POST"])
@prof_required
def upload():
    prof_id=session["prof_id"]  
    course_title=request.form["course_title"]
    material=request.files.getlist("files")
    course_id=ingest_course_files(material,prof_id,collection,course_title)
    return jsonify({"course_id":course_id})




@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged out"})

rp.init_db()
app.run(debug=True)