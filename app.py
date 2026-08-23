from flask import Flask,request, Response, jsonify,render_template
import os
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
    ingest_course,
    create_course,
    create_professor,
    get_professor_by_token,
    get_user_chats,
    rotate_token,
    get_professor_courses,
    validate_key
)
app=Flask(__name__)
from rag_pipeline import embedder, collection, openai_key, db_path
k=8

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


@app.route("/professor",methods=["POST"])
def professor_route():
    data=request.json
    if not validate_key(data["api_key"],data["model"]):
        return jsonify({"error":"invalid key or model"}),400
    
    prof_id,token=create_professor(data["name"],data["api_key"],data["model"])
    return jsonify({"professor_id": prof_id, "share_token": token})

@app.route("/signup")
def sign_up_page():
    return render_template("prof_signup.html")

@app.route("/professor_courses",methods=["GET"])
def professor_courses():
    prof_id=request.args.get("prof_id")
    course_rows=get_professor_courses(prof_id)
    course_list=[{"course_id":c[0],"course_title":c[1]} for c in course_rows]
    return jsonify({"courses":course_list})

@app.route("/delete_courses",methods=["POST"])
def delete_course():
    course_id=request.json["course_id"]
    prof_id=request.json["prof_id"]
    delete_course(course_id,prof_id)
    return jsonify({"status":"deleted"})


@app.route("/ingest",methods=["POST"])
def upload():
    prof_id=request.form["prof_id"]
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
def create_convo():
    course_id=request.json["course_id"]
    prof_id=request.json["professor_id"]
    chat_id=create_conversation(prof_id,course_id, "New chat")
    return jsonify({"chat_id":chat_id})



init_db()
app.run(debug=True)