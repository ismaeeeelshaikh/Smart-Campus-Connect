# Smart Campus Connect

An AI chatbot for **A.P. Shah Institute of Technology (APSIT), Thane**. It answers questions about admissions, departments, faculty, facilities and placements.

- **APSIT students** sign up with their `@apsit.edu.in` email and an OTP, and get saved ChatGPT-style chats.
- **Visitors** (future students, parents) can chat as a guest without an account.

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
uvicorn app.main:app
```

After editing `backend/.env`, stop the backend (Ctrl+C) and start it again. (`--reload` is avoided on purpose: on Windows it sometimes gets stuck and keeps running the old code and settings.)

- API: http://127.0.0.1:8000
- Interactive API docs: http://127.0.0.1:8000/docs

The first start takes several minutes: the embedding model is downloaded (~440 MB) and the knowledge base is indexed. Later starts take about a minute on Windows, and only changed data files are re-indexed.

## 2. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api/*` requests to the backend on port 8000.

## Knowledge base

The chatbot answers from the text files in `backend/college_data/`, indexed into a vector database stored in `backend/chroma_db/` (git-ignored).

- **To change the data:** edit, add or delete `.txt` files, then restart the backend. At startup only the files whose content changed are re-indexed.
- **File format:** the first line can be an ALL-CAPS title. `=== SECTION NAME ===` lines split the file into sections; each chunk keeps its title and section name, which helps search.
- **Rebuild from scratch** (stop the backend first): `python -m scripts.build_index --rebuild`

Search is hybrid. Meaning-based (vector) search is combined with keyword search, so exact terms like "DTE code", names and abbreviations are found too.

Use these files only for information that is **not** on the college website. Everything on the website is read automatically (next section), and website information wins when the two disagree.

## Live sync with apsit.edu.in

The backend keeps its knowledge in sync with https://www.apsit.edu.in, so changes made on the college website reach the chatbot without anyone editing files.

- **Automatic:** every `CRAWL_INTERVAL_HOURS` (default 6) the whole site is crawled. Only pages whose text changed are re-indexed, and deleted pages are removed. The first full sync takes about 40 minutes (1,300+ pages plus the 60 newest PDFs); later syncs mostly re-check pages and re-index only what changed.
- **What is read:**
  - the main content of every page, without the menu, sidebar or footer
  - faculty cards (one line per person)
  - contact details, with Cloudflare-hidden emails decoded
  - the text of the newest PDFs, skipping merit lists and student lists, which contain personal data
- **Admins** (emails in `ADMIN_EMAIL`, comma-separated) see a **Website sync** button in the header. It has:
  - **Sync now:** a full sync in the background, with live progress, the last result and recently changed pages
  - **Update one page:** paste the link of a page that was just edited, and it's re-read in a few seconds
- **Answers cite their sources:** when an answer uses website content, it ends with "Source:" and the page link.

Settings (all optional, in `backend/.env`): `CRAWL_INTERVAL_HOURS` (0 = automatic sync off), `CRAWL_MAX_PAGES`, `CRAWL_DELAY_SECONDS`, `CRAWL_INCLUDE_PDFS`, `CRAWL_MAX_PDFS`.

## Guest mode

Visitors without an `@apsit.edu.in` email (future students, parents) can click **Chat as guest** on the login page (or open `/guest`). They can ask the same questions; guest chats are not saved and disappear when the tab is closed.

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
    routers/          API endpoints (auth, chat sessions, guest chat, password reset)
    services/         business logic (auth, OTP, email, knowledge base, RAG,
                      website crawler + sync)
    schemas/          request/response models
  alembic/            database migrations
  college_data/       knowledge base text files
  scripts/            check_db.py, check_groq.py, build_index.py
frontend/
  src/
    components/       Auth, Chat, Layout, Sidebar
    context/, hooks/  auth state, chat sessions
    services/         API client
```

## Security

- Never commit `backend/.env`. It is git-ignored; `backend/.env.example` lists the keys without values.
- `JWT_SECRET` should be long and random: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- **Signup** is limited to `ALLOWED_SIGNUP_DOMAINS` (default `apsit.edu.in`) and needs an emailed OTP.
- **OTPs** are 6 random digits (`secrets`), stored only as an HMAC hash, valid 10–15 minutes, and stop working after 5 wrong guesses. Requesting a new code cancels the old one.
- **Passwords:** 8–128 characters with uppercase, lowercase and a number; hashed with argon2. A password reset logs out every other session.
- **Rate limits:** too many login, OTP or password-reset requests get `429 Too many attempts` (per email and per IP). Chat is not rate-limited.
- **API responses** carry security headers (`nosniff`, `X-Frame-Options: DENY`, ...).
- **In production:** set `ENABLE_DOCS=false`. Set `TRUST_PROXY_HEADERS=true` only behind a reverse proxy.
- **The website crawler** only follows redirects within `www.apsit.edu.in`.
