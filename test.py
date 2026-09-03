from rag_pipeline import init_db , create_professor, ingest_course, create_conversation, ask
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
embedder=SentenceTransformer("all-MiniLM-L6-v2")

load_dotenv()
openai_key=os.getenv("OPENAI_API_KEY")
db_path="app.db"
client=chromadb.PersistentClient("./chroma_db")
collection=client.get_or_create_collection(name="courses")

init_db()
prof_id,token=create_professor("hadi",openai_key,"gpt-4o")
course_id = ingest_course("Hashing.pdf", prof_id, collection)
chat_id = create_conversation(prof_id, course_id, "Test chat")
ask("what is double hashing?", chat_id, "gpt-4o", 6, collection, embedder, openai_key, course_id)


