import requests

BASE = "http://127.0.0.1:5000"

# 1. create a professor
r = requests.post(f"{BASE}/professor", json={
    "name": "Hadi",
    "api_key": "",   # paste your real key, or load from .env
    "model": "gpt-4o"
})
print("PROFESSOR:", r.status_code, r.json())
prof_id = r.json()["professor_id"]
token = r.json()["share_token"]

# 2. upload a course (note: field names must match the route — prof_id, course_title, files)
r = requests.post(f"{BASE}/ingest",
    data={"prof_id": prof_id, "course_title": "Hashing"},
    files=[("files", open("Hashing.pdf", "rb"))]
)
print("INGEST:", r.status_code, r.json())
course_id = r.json()["course_id"]

# 3. landing — resolve the token
r = requests.get(f"{BASE}/tutor/{token}")
print("LANDING:", r.status_code, r.json())

# 4. create a conversation (note: this route uses professor_id, not prof_id)
r = requests.post(f"{BASE}/create_convo", json={
    "professor_id": prof_id,
    "course_id": course_id
})
print("CONVO:", r.status_code, r.json())
chat_id = r.json()["chat_id"]

# 5. chat
r = requests.post(f"{BASE}/chat", json={
    "question": "what is double hashing?",
    "chat_id": chat_id,
    "course_id": course_id
})
print("CHAT:", r.status_code)
print(r.text)