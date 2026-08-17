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

embedder=SentenceTransformer("all-MiniLM-L6-v2")

load_dotenv()
openai_key=os.getenv("OPENAI_API_KEY")


client=chromadb.PersistentClient("./chroma_db")
collection=client.get_or_create_collection(name="courses")

def init_db(db_path):
    conn=sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages(
            message_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
            )
        """)
    conn.commit()
    conn.close()


def save_messages(chat_id,role,content,db_path):
    conn=sqlite3.connect(db_path)
    cur=conn.cursor()
    cur.execute(
        
        "INSERT INTO messages (chat_id,role,content,timestamp) VALUES (? ,? ,? ,?)",
        (chat_id,role,content,datetime.now().isoformat())
        
    )
    conn.commit()
    conn.close()

def get_history(chat_id,db_path):
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
        if page:
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
def store_to_db(chunks,Collection):
    Collection.upsert(
        ids=[ f"chunk_{i}" for i in range(len(chunks)) ],
        embeddings=[i["vector"] for i in chunks],
        documents=[i["text"] for i in chunks],
        metadatas=[{"page": i["page"]} for i in chunks]
        )
    return len(chunks)


def retrieve(question,k,Collection,embedder):
    q_vector=embedder.encode(question).tolist()
    results=Collection.query(query_embeddings=[q_vector],n_results=k)
    return results

def answer(question,k,llm,Collection,embedder,api_key):
    results=retrieve(question,k,Collection,embedder)
    chunks=results["documents"][0]
    pages = results["metadatas"][0]
    context="\n\n".join(
        f"[slide {p['page']}] {text} " for text, p in zip(chunks , pages)
    )
    system_prompt= "Answer the question using only the provided context. If the answer isn't in the context, say so."
    response=completion(
        model=llm,
        api_key=api_key,
        messages=[{"role":"system","content":system_prompt},
                {"role":"user" , "content" : f"Context : {context}\n\n question:{question}"}
            ],
        stream=True
    )
    for chunk in  response:
        piece=chunk.choices[0].delta.content
        if piece:
            yield piece
    
def get_msg(question,k,llm,collection,embedder,api_key):
    full=""
    for piece in answer(question,k,llm,collection,embedder,api_key):
        full+=piece
    return full

test_question="how do i handle collision in hashing?"

def test_run(pdf,test_question,llm,k,Collection,embedder,api_key):
    pages=extract_pages(pdf)
    chunks=chunking(pages)
    embedded_chunks=embedding(chunks)
    store_to_db(embedded_chunks,Collection)
    full=""
    print(f"Q: {test_question}\n")

    for piece in answer(test_question,k,llm,Collection,embedder,api_key):
        print(piece,end="",flush=True)
        full+=piece
    

test_run("Hashing.pdf",test_question,"gpt-4o",3,collection,embedder,openai_key)






