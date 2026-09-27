# TutorApp

An AI tutoring platform where professors turn their course PDFs into a retrieval-augmented chatbot that students can ask questions against — grounded in the actual course material, not general knowledge.

## Features

### Professor side
- **Signup with your own LLM key** — professors sign up with an API key and a model name (e.g. an OpenAI model); the key is validated with a live test call before the account is created, then encrypted at rest (Fernet) and only decrypted server-side when answering a question.
- **Course creation via PDF upload** — upload one or more PDFs for a course; each is parsed, chunked, embedded, and stored so students can immediately start asking questions about it.
- **Shareable invite link** — each professor gets a unique token-based link; students who open it are routed into that professor's course list for signup/login. The token can be rotated to invalidate old links.
- **Course management** — list and delete courses (deleting a course cascades to its conversations, messages, and stored embeddings).
- **Student question log** — see every question students have asked in a given course, most recent first — useful for spotting common points of confusion.

### Student side
- **Access is invite-based** — students can only sign up/log in through a professor's share link, then pick from that professor's courses.
- **Grounded Q&A chat** — ask questions about the course material and get streamed, context-aware answers.
- **Multiple conversations per course** — chat history persists; students can revisit, rename, or delete past conversations, and each conversation is auto-titled from its first question.
- **Conversational memory** — recent turns in a chat are folded into the retrieval query, so follow-up questions ("what about the second one?") still pull relevant context.

### RAG pipeline
- PDF text is extracted per page (`pypdf`), split into overlapping chunks (`langchain-text-splitters`), and embedded with a local `sentence-transformers` model (`all-MiniLM-L6-v2`) — no API calls needed for embedding.
- Embeddings are stored in Postgres with `pgvector`, scoped per course, and queried with vector similarity search to fetch the top-k most relevant chunks for a question.
- Answers are generated via `litellm`, so each professor's configured model/provider is used to answer their own students' questions, with the retrieved chunks injected as grounding context and a system prompt that keeps the assistant on-topic and honest about what isn't covered in the material.

### Security & platform
- Student and professor accounts are fully separate, session-based auth domains with their own login/signup flows and route guards.
- Passwords are hashed with Werkzeug; professor LLM API keys are encrypted with Fernet rather than stored in plaintext.
- Auth and chat endpoints are rate-limited (`Flask-Limiter`) per user/IP to curb abuse.
- The Flask backend also serves the built React frontend directly, so the whole app runs as a single deployable unit.

## Tech stack

**Backend:** Flask, PostgreSQL + `pgvector`, `psycopg`, `sentence-transformers`, `litellm`, `Flask-Limiter`, `cryptography` (Fernet)
**Frontend:** React (Vite), React Router

## Setup

### Backend
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Provision a PostgreSQL database with the `pgvector` extension available, then create a `.env` file in the project root:
   ```
   DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>
   app_secret_key=<a random secret key for Flask sessions>
   FERNET_KEY=<a Fernet key, e.g. from Fernet.generate_key()>
   ```
3. Run the backend:
   ```bash
   python app.py
   ```
   Tables (including the `vector` extension and `embeddings` table) are created automatically on startup.

### Frontend
```bash
cd my-frontend
npm install
npm run build
```
The Flask app serves the built files from `my-frontend/dist`, so once built, the whole app is available from the Flask server's URL. For frontend-only iteration, `npm run dev` runs the Vite dev server instead.
