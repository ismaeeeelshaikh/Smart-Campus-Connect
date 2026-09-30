from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import auth, chat, chat_sessions, password_reset

app = FastAPI(
    title="College AI Chatbot",
    description="AI-powered chatbot for college information with chat sessions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(chat_sessions.router)
app.include_router(password_reset.router) 

@app.get("/")
async def root():
    return {"message": "College AI Chatbot API with Chat Sessions"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}