import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import auth, chat_sessions, guest, password_reset
from .services.rag import init_rag_service

# Configure logging once for the whole app (modules only call logging.getLogger)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loading the embedding model is slow and blocking, so do it in a thread
    await asyncio.to_thread(init_rag_service)
    yield


app = FastAPI(
    title="Smart Campus Connect API",
    description="AI-powered chatbot for APSIT college information",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(guest.router)
app.include_router(password_reset.router)

@app.get("/")
async def root():
    return {"message": "Smart Campus Connect API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
