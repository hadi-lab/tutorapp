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

def course_belongs_to_prof(course_id,prof_id):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("""
        SELECT 1 FROM courses WHERE professor_id=? AND course_id=?
        """,(prof_id,course_id))
    row=cur.fetchone()
    conn.close()
    return row is not None




def chat_belong_to_student(chat_id,s_id):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("SELECT 1 FROM conversations WHERE chat_id=? AND student_id=?",(chat_id,s_id))
    row=cur.fetchone()
    conn.close()
    return row is not None

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
    conn=sqlite3.connect(db_path)
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

def get_token_by_prof_id(prof_id):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("SELECT share_link_token FROM professors WHERE professor_id =?",(prof_id,))
    row=cur.fetchone()
    conn.close()
    return row[0] if row else None

def create_conversation(student_id, course_id):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO conversations (student_id, course_id, title, created_at) VALUES (?, ?, ?, ?)",
        (student_id, course_id, None, datetime.now().isoformat())
    )
    chat_id = cur.lastrowid          
    conn.commit()
    conn.close()
    return chat_id




def answer(question, k, chat_id, llm, Collection, embedder, api_key, course_id):
    history=get_history(chat_id)
    retrieval_query = question
    if history:
        recent_user_msgs = [content for role, content in history if role == "user"][-2:]
        if recent_user_msgs:
            retrieval_query = " ".join(recent_user_msgs) + " " + question


    results=retrieve(retrieval_query, k, Collection, embedder, course_id)
    chunks=results["documents"][0]
    pages = results["metadatas"][0]
    context="\n\n".join(
        f"[slide {p['page']}] {text} " for text, p in zip(chunks , pages)
    )
    system_prompt = """You are a knowledgeable and patient tutor for this specific course. Your role is to help students understand the course material.

            GROUNDING:
            - Base your answers on the provided context from the course materials. This is your source of truth.
            - You may explain, rephrase, simplify, give examples, and draw connections between concepts in the context to aid understanding.
            - If the context doesn't cover something the student asks, say so honestly, but still try to be helpful — offer to explain related concepts that ARE in the material, or help them rephrase their question.
            - Do not state facts as course content if they aren't supported by the context. If you add general knowledge to help, make it clear that's supplementary.

            TEACHING STYLE:
            - Explain clearly and at a level appropriate for a student learning the material.
            - When asked to simplify, use analogies or plain language.
            - Be encouraging and conversational, not robotic.
            - For greetings or casual messages, respond naturally and warmly, then invite course questions.

            STAY ON TOPIC:
            - Gently redirect off-topic requests back to the course material.
            - You are a tutor for this course, not a general assistant."""
    

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
    cur.execute("""
            SELECT c.chat_id,c.title,c.course_id,co.title  FROM  conversations c
            JOIN courses co ON c.course_id=co.course_id
            WHERE c.student_id=? AND c.title IS NOT NULL
            ORDER BY c.created_at DESC
            """,(student_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

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

def get_title(c_id):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("SELECT title FROM courses WHERE course_id=?",(c_id,))
    row=cur.fetchone
    conn.close()
    return row[0] if row else None

def insert_title(title,chat_id):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute("UPDATE conversations SET title=? WHERE chat_id=?",(title,chat_id))
    conn.commit()
    conn.close()

def delete_chat(s_id,chat_id):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute(" DELETE FROM messages WHERE chat_id=?",(chat_id,))
    cur.execute(" DELETE FROM conversations WHERE chat_id=?",(chat_id,))
    conn.commit()
    conn.close()


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
