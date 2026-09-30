import logging

# Configure logging once for the whole app (modules only call logging.getLogger).
# Must run before the routers are imported, because importing them starts the RAG service.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import auth, chat_sessions, password_reset

app = FastAPI(
    title="Smart Campus Connect API",
    description="AI-powered chatbot for APSIT college information",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat_sessions.router)
app.include_router(password_reset.router)

@app.get("/")
async def root():
    return {"message": "Smart Campus Connect API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
