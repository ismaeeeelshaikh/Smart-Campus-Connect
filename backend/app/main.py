import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import admin, auth, chat_sessions, guest, health, password_reset
from .services import website_sync
from .services.rag import init_rag_service

# Configure logging once for the whole app (modules only call logging.getLogger)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loading the embedding model is slow and blocking, so do it in a thread
    await asyncio.to_thread(init_rag_service)
    await website_sync.mark_interrupted_runs()
    scheduler = asyncio.create_task(website_sync.schedule_loop())
    yield
    scheduler.cancel()


app = FastAPI(
    title="Smart Campus Connect API",
    description="AI-powered chatbot for APSIT college information",
    version="1.0.0",
    lifespan=lifespan,
    # Interactive docs are handy in development; set ENABLE_DOCS=false in production
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")  # don't guess file types
    response.headers.setdefault("X-Frame-Options", "DENY")            # can't be shown inside another site's iframe
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(chat_sessions.router)
app.include_router(guest.router)
app.include_router(health.router)
app.include_router(password_reset.router)

@app.get("/")
async def root():
    return {"message": "Smart Campus Connect API"}
