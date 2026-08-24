from sentence_transformers import SentenceTransformer
import numpy as np
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from litellm import completion
import os
import chromadb
import sqlite3
from dotenv import load_dotenv
from datetime import datetime
import secrets
from litellm.exceptions import AuthenticationError
embedder=SentenceTransformer("all-MiniLM-L6-v2")
db_path="app.db"
load_dotenv()
openai_key=os.getenv("OPENAI_API_KEY")


client=chromadb.PersistentClient("./chroma_db")
collection=client.get_or_create_collection(name="courses")

import sqlite3

def init_db():
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS professors (
        professor_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        hashed_pass TEXT,
        name       TEXT,
        api_key     TEXT,
        model            TEXT,
        share_link_token     TEXT UNIQUE
        );

        CREATE TABLE IF NOT EXISTS courses (
        course_id  INTEGER PRIMARY KEY AUTOINCREMENT,
        professor_id INTEGER,
        title      TEXT,
        created_at TEXT,
        FOREIGN KEY (professor_id) REFERENCES professors(professor_id)
        );

        CREATE TABLE IF NOT EXISTS students (
            student_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            email          TEXT UNIQUE,
            password_hash  TEXT
        );


        CREATE TABLE IF NOT EXISTS conversations (
            chat_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id   INTEGER,
            course_id   INTEGER,
            title       TEXT,
            created_at  TEXT,
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_id) REFERENCES courses(course_id)
        );
        

        CREATE TABLE IF NOT EXISTS messages (
            message_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id     INTEGER,
            role        TEXT,
            content     TEXT,
            timestamp   TEXT,
            FOREIGN KEY (chat_id) REFERENCES conversations(chat_id)
        );
    """)
    conn.commit()
    conn.close()

def delete_course(course_id,prof_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""DELETE FROM messages WHERE chat_id IN
                (SELECT chat_id FROM conversations WHERE course_id = ?)""", (course_id,))
    cur.execute("DELETE FROM conversations WHERE course_id = ?", (course_id,))
    cur.execute("DELETE FROM courses WHERE course_id = ? AND professor_id=?", (course_id,prof_id))
    conn.commit()
    conn.close()
    collection.delete(where={"course_id": course_id})
def save_messages(chat_id,role,content):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute(
        
        "INSERT INTO messages (chat_id,role,content,timestamp) VALUES (? ,? ,? ,?)",
        (chat_id,role,content,datetime.now().isoformat())
        
    )
    conn.commit()
    conn.close()

def get_history(chat_id):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE chat_id = ? ORDER BY message_id",
        (chat_id,)
    )
    rows=cur.fetchall()
    conn.close()
    return rows


def extract_pages(pdf):
    pages=[]
    reader=PdfReader(pdf)
    for i, page in enumerate(reader.pages):
        page_text=page.extract_text()
        if page_text:
            pages.append({
                "text":page_text,"page": i + 1
            })
    return pages

def chunking(pages):
    chunks=[]
    splitter=RecursiveCharacterTextSplitter(chunk_size=800,chunk_overlap=100)
    for page in pages:
        pieces=splitter.split_text(page["text"])
        for piece in pieces:
            chunks.append({"text" : piece , "page" : page["page"]})
    return chunks

def embedding(chunks):
    for c in  chunks:
        c["vector"]=embedder.encode(c["text"]).tolist()
    return chunks

def store_to_db(chunks,Collection,course_id, file_id):
    Collection.upsert(
        ids=[ f"{course_id}_{file_id}_chunk_{i}" for i in range(len(chunks)) ],
        embeddings=[i["vector"] for i in chunks],
        documents=[i["text"] for i in chunks],
        metadatas=[{"page": i["page"], "course_id": course_id} for i in chunks]
        )
    return len(chunks)


def retrieve(question,k,Collection,embedder,course_id):
    q_vector=embedder.encode(question).tolist()
    results=Collection.query(query_embeddings=[q_vector],n_results=k,where={"course_id": course_id})
    return results

def get_students_by_email(email):
    conn=sqlite3.connect()
    cur=conn.cursor()
    cur.execute("SELECT student_id,password_hash FROM students WHERE email = ?",(email,))
    row=cur.fetchone()
    conn.close()
    return row

def get_prof_by_email(email):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("SELECT professor_id,hashed_pass FROM professors WHERE  email=? ",(email,))
    row=cur.fetchone()
    conn.close()
    return row



def create_conversation(student_id, course_id, title):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (student_id, course_id, title, created_at) VALUES (?, ?, ?, ?)",
        (student_id, course_id, title, datetime.now().isoformat())
    )
    chat_id = cur.lastrowid          
    conn.commit()
    conn.close()
    return chat_id




def answer(question, k, chat_id, llm, Collection, embedder, api_key, course_id):
    results=retrieve(question, k, Collection, embedder, course_id)
    chunks=results["documents"][0]
    pages = results["metadatas"][0]
    context="\n\n".join(
        f"[slide {p['page']}] {text} " for text, p in zip(chunks , pages)
    )
    system_prompt= "Answer the question using only the provided context. If the answer isn't in the context, say so."

    history=get_history(chat_id)

    messages=[{"role":"system","content":system_prompt }]
    
    for role,content in history:
        messages.append({"role":role,"content":content})
    messages.append({"role":"user","content": f"context: {context} \n\n question:{question}"})

    response=completion(
        model=llm,
        api_key=api_key,
        messages=messages,
        stream=True
    )
    for chunk in  response:
        piece=chunk.choices[0].delta.content
        if piece:
            yield piece

def ask(question,chat_id,llm,k,collection,embedder,api_key,course_id):
    full=""
    for piece in answer(question,k,chat_id,llm,collection,embedder,api_key,course_id):
        print(piece,end="",flush=True)
        full+=piece
    save_messages(chat_id, "user", question)   
    save_messages(chat_id, "assistant", full)


def create_course(title,prof_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO courses (professor_id,title,created_at) VALUES (?,?,?)", (prof_id,title,datetime.now().isoformat()))
    course_id = cur.lastrowid  
    conn.commit()
    conn.close()
    return course_id 


def create_student(email,password_hash):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("INSERT INTO students(email,password_hash) VALUES (?,?)",(email,password_hash))
    student_id=cur.lastrowid
    conn.commit()
    conn.close()
    return student_id

def create_professor(name,email,hashed_pass,api_key,model):
    token=secrets.token_urlsafe(32)
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute(
            "INSERT INTO professors(name,email,hashed_pass,api_key,model,share_link_token) VALUES (?,?,?,?,?,?)",
            (name,email,hashed_pass,api_key,model,token)
    )
    professor_id=cur.lastrowid
    conn.commit()
    conn.close()
    return professor_id,token

def get_professor_by_token(token):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute(
        "SELECT professor_id,api_key,model FROM professors WHERE share_link_token=?",(token,)
    )
    row=cur.fetchone()
    conn.close()
    return row

def get_user_chats(student_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT chat_id, title FROM conversations WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
    rows = cur.fetchall()
    conn.close()
    return rows      # [(1, "Hashing questions"), (2, "Trees"), ...]

def rotate_token(professor_id):
    new_token=secrets.token_urlsafe(32)
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("UPDATE professors SET share_link_token=? WHERE professor_id=?",(new_token,professor_id))
    conn.commit()
    conn.close()
    return new_token

def get_professor_courses(prof_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT course_id, title FROM courses WHERE professor_id = ?",
        (prof_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows

def get_professor_for_chat(chat_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.api_key, p.model
        FROM conversations c
        JOIN courses co ON c.course_id = co.course_id
        JOIN professors p ON co.professor_id = p.professor_id
        WHERE c.chat_id = ?
    """, (chat_id,))
    row = cur.fetchone()
    conn.close()
    return row






def validate_key(api_key, model):
    try:
        completion(
            model=model,
            api_key=api_key,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1              # keep it tiny/cheap
        )
        return True
    except AuthenticationError:
        return False
    except Exception:
        return False                  # any other failure = treat as invalid
#STEPS TO DO
#Professor scoping in retrieval — add professor_id to the metadata filter so one professor's students never see another's courses (you have course_id filtering; add the professor layer).
#The share-token flow — create_professor mints a token; get_professor_by_token resolves a link to a professor's id/key/model.
#The web layer — this is the big one. Wrap your functions as endpoints: an upload/ingest endpoint for professors, a chat endpoint for students that streams over HTTP. Your streaming generator drops right into this. This is where it stops being a terminal script and becomes a real app with the public link.
#The student interface — the actual page students land on via the link (anonymous, pick a course, chat).
#Before going public — encrypt the stored API key, add per-link rate limiting, allow token rotation.