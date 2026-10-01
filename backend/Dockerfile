# Backend: FastAPI + the embedding model. CPU only: the LLM runs on another server (Groq / college DGX).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface \
    ANONYMIZED_TELEMETRY=False

WORKDIR /app

# CPU-only PyTorch first: the default wheel adds gigabytes of CUDA libraries this server doesn't use
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# Put the embedding model (~440 MB) into the image, so a container starts without downloading it.
# If you change EMBEDDING_MODEL, rebuild with: docker compose build --build-arg EMBEDDING_MODEL=<name>
ARG EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}')"
ENV HF_HUB_OFFLINE=1

COPY . .

# Run as a normal user. chroma_db/ (the knowledge base) is a volume, see docker-compose.yml.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/chroma_db \
    && chown -R app:app /app/chroma_db /opt/huggingface
USER app

EXPOSE 8000
# Exactly one process (no --workers): the website-sync scheduler, its progress and the rate limits
# live in this process's memory. The database tables are created/updated before the API starts.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
