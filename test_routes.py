import requests
import time
email = f"hadi{int(time.time())}@test.com"
BASE = "http://127.0.0.1:5000"

# ---- Test 1: protected route WITHOUT logging in (should be blocked) ----
r = requests.get(f"{BASE}/professor_courses")     # fresh request, no session
print("NO AUTH:", r.status_code, r.json())        # expect 401 "not logged in"

# ---- Test 2: full flow WITH a session ----
s = requests.Session()      # <- persists cookies across all calls made with `s`

# signup (sets the session cookie on `s`)
r = s.post(f"{BASE}/professor_signup", json={
    "name": "Hadi",
    "email": email,
    "password": "mypassword",
    "api_key": "",       # real key, or load from .env
    "model": "gpt-4o"
})
print("SIGNUP:", r.status_code)
print(r.text) 

# now protected routes work, because `s` carries the session cookie

# ingest a course (no prof_id sent — comes from session)
r = s.post(f"{BASE}/ingest",
    data={"course_title": "Hashing"},
    files=[("files", open("Hashing.pdf", "rb"))]
)
print("INGEST:", r.status_code, r.json())
course_id = r.json()["course_id"]

# list courses (prof_id from session)
r = s.get(f"{BASE}/professor_courses")
print("COURSES:", r.status_code, r.json())

# ---- Test 3: login as returning professor (new session) ----
s2 = requests.Session()
r = s2.post(f"{BASE}/professor_login", json={
    "email": email,
    "password": "mypassword"
})
print("LOGIN:", r.status_code, r.json())

# s2 is now logged in — protected routes work
r = s2.get(f"{BASE}/professor_courses")
print("COURSES AFTER LOGIN:", r.status_code, r.json())

# ---- Test 4: wrong password (should fail) ----
s3 = requests.Session()
r = s3.post(f"{BASE}/professor_login", json={
    "email": email,
    "password": "wrongpassword"
})
print("WRONG PASSWORD:", r.status_code, r.json())   # expect 401