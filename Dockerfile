# --- Stage 1: build the React frontend ---
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY my-frontend/package.json my-frontend/package-lock.json ./
RUN npm ci
COPY my-frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime ---
FROM python:3.12.8-slim AS backend
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the embedding model into the image so containers don't hit
# HuggingFace on every cold start.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY app.py rag_pipeline.py ./
COPY --from=frontend /frontend/dist ./my-frontend/dist

EXPOSE 8080
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--threads", "4", "--timeout", "120"]
