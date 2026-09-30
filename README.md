# Smart Campus Connect

An AI chatbot for **A.P. Shah Institute of Technology (APSIT), Thane**. Students sign up with an email OTP, chat in ChatGPT-style sessions, and get answers about admissions, departments, faculty, facilities and placements.

- **Backend:** FastAPI, async SQLAlchemy + PostgreSQL, Alembic, JWT auth
- **AI:** retrieval-augmented generation (LangChain + Chroma + `BAAI/bge-base-en-v1.5` embeddings) with a Groq-hosted LLM
- **Frontend:** React 18 + Vite + Tailwind CSS

Work in progress: see [ROADMAP.md](ROADMAP.md) for the step-by-step plan to make this production-ready (including live sync with apsit.edu.in).

---

## Requirements

| Tool | Version | Notes |
|---|---|---|
| Python | **3.12** | 3.13+ is not yet supported by some ML packages |
| PostgreSQL | 14+ | |
| Node.js | 18+ | |
| Groq API key | | Free at https://console.groq.com/keys |
| Gmail account with an App Password | | Sends the OTP emails. Create one at https://myaccount.google.com/apppasswords (needs 2-Step Verification) |

The commands below are for Windows PowerShell.

## 1. Backend

```powershell
cd backend

# Virtual environment + packages (first install takes a few minutes: it includes PyTorch)
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Configuration: copy the example, then open backend\.env and fill in every value
copy .env.example .env
```

Create the database once. Use pgAdmin, or:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -c "CREATE DATABASE college_ai;"
```

Create the tables, then (optionally) check that the database and Groq key work:

```powershell
alembic upgrade head
python -m scripts.check_db
python -m scripts.check_groq
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs

The first start takes longer because the embedding model is downloaded (~440 MB) and the knowledge base is indexed.

## 2. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api/*` requests to the backend on port 8000.

## Knowledge base

The chatbot answers from the text files in `backend/college_data/`. The index is rebuilt from these files every time the backend starts, so to change the data: edit or add `.txt` files, then restart the backend.

Phase 4 of the roadmap replaces this with an automatic crawler, so changes on apsit.edu.in reach the chatbot without editing files.

## Database migrations

After changing a model in `backend/app/models/`:

```powershell
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

Review the generated file in `backend/alembic/versions/` before committing it.

## Project structure

```
backend/
  app/
    main.py           FastAPI app, CORS, routers
    config.py         all settings, loaded from backend/.env
    database.py       async SQLAlchemy engine + session
    models/           database tables
    routers/          API endpoints (auth, chat sessions, password reset)
    services/         business logic (auth, OTP, email, RAG)
    schemas/          request/response models
  alembic/            database migrations
  college_data/       knowledge base text files
  scripts/            check_db.py, check_groq.py
frontend/
  src/
    components/       Auth, Chat, Layout, Sidebar
    context/, hooks/  auth state, chat sessions
    services/         API client
```

## Security

- Never commit `backend/.env`. It is git-ignored; `backend/.env.example` lists the keys without values.
- `JWT_SECRET` should be long and random: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
