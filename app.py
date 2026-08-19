from flask import Flask,request, Response, jsonify
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

def add_file_to_course(pdf, course_id, collection):
    pages = extract_pages(pdf)
    chunks = chunking(pages)
    embedded = embedding(chunks)
    store_to_db(embedded, collection, course_id)    
    return len(embedded)

def ingest_course_files(files,prof_id,collection,course_title):
    course_id=create_course(course_title,prof_id)
    for file in files:
        file_id=os.path.splitext(file.filename)[0]
        path=f"./uploads/{prof_id}/{file.filename}"
        file.save(path)
        add_file_to_course(path,course_id,collection)

from rag_pipeline import embedder, collection, openai_key, db_path
k=8
app=Flask(__name__)

@app.route("/chat",methods=["POST"])
def ask_endpoint():
    question=request.json["question"]
    chat_id=request.json["chat_id"]
    course_id=request.json["course_id"]
    prof=get_professor_for_chat(chat_id)
    api_key=prof["api_key"]
    llm=prof["model"]
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

@app.route("/upload",methods=["POST"])
def upload():
    prof_id=request.form["prof_id"]
    
