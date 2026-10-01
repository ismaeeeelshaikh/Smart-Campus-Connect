# Smart Campus Connect

An AI chatbot for **A.P. Shah Institute of Technology (APSIT), Thane**. It answers questions about admissions, departments, faculty, facilities and placements.

- **APSIT students** sign up with their `@apsit.edu.in` email and an OTP, and get saved ChatGPT-style chats.
- **Visitors** (future students, parents) can chat as a guest without an account.

- **Backend:** FastAPI, async SQLAlchemy + PostgreSQL, Alembic, JWT auth
- **AI:** retrieval-augmented generation (LangChain + Chroma + `BAAI/bge-base-en-v1.5` embeddings) with any OpenAI-compatible LLM: Groq for now, a self-hosted model on the college DGX server later
- **Frontend:** React 18 + Vite + Tailwind CSS
- **Deployment:** Docker Compose with PostgreSQL and Caddy (HTTPS); see [DEPLOYMENT.md](DEPLOYMENT.md)

The step-by-step plan that made this production-ready is in [ROADMAP.md](ROADMAP.md).

---

## Requirements

| Tool | Version | Notes |
|---|---|---|
| Python | **3.12** | 3.13+ is not yet supported by some ML packages |
| PostgreSQL | 14+ | |
| Node.js | 18+ | |
| LLM API key | | For now Groq: free at https://console.groq.com/keys (see [LLM](#llm)) |
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

Create the tables, then (optionally) check that the database and the LLM work:

```powershell
alembic upgrade head
python -m scripts.check_db
python -m scripts.check_llm
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

- **Lint:** `npm run lint` (ESLint 9, flat config in `eslint.config.js`).
- **Production build:** `npm run build` → `frontend/dist/`. If the API is on another address, set `VITE_API_URL` at build time (see `frontend/.env.example`).

### Design

The UI uses an "APSIT Heritage" design system taken from the college crest: deep teal (`#145C5F`), saffron gold (`#E0A91B`), crimson (`#A51D2D`, used sparingly) on warm paper (`#F7F4EC`). Headings are in Literata (serif), text in Hanken Grotesk. Both fonts are bundled with the app, so no Google Fonts request is made. The tokens are in `frontend/tailwind.config.js`; shared button, input and card styles are in `src/index.css`. The first concepts were drafted in Google Stitch (project "Smart Campus Connect (APSIT)").

### Chat features

- **Streaming:** answers appear word by word over server-sent events (`/chat-sessions/start/stream`, `/chat-sessions/{id}/messages/stream`, `/guest/chat/stream`).
- **Sources:** each answer shows source chips that link the website pages it used. The backend keeps only pages that were really in the retrieved context, so a link the model invents is dropped. Sources are saved with each message.
- **Formatting:** answers render as markdown, including tables (GitHub-flavoured markdown).
- **Copy, retry and voice:**
  - copy button on every answer
  - "Try again" when a question fails
  - voice input (Chrome/Edge, `en-IN`) that asks for the microphone only when you press the mic
- **Mobile:** the sidebar becomes a drawer behind the menu button.
- **Languages:** ask in English, Hindi, Marathi or Hinglish and the answer comes back in the same language (Hinglish in English letters). Non-English questions are translated into English for the search, because the website data is English. Names, numbers and links stay exactly as on the website.
- **Profile:** students sign up with their full name (not a unique username) and can change it from the sidebar.
- **Ask about a PDF:** students can attach a PDF (notice, syllabus, timetable…) with the paperclip and ask about it; see [PDF upload](#pdf-upload).

## PDF upload

Logged-in students can attach one PDF per chat (the paperclip in the message box). Guests can't, because uploads use the server's CPU and belong to a saved chat.

- **What's kept:** only the PDF's text, split into chunks, stored with the chat in PostgreSQL. The file itself isn't stored. Deleting the chat deletes the PDF; a new upload replaces the old one.
- **Fast upload:** the text is read and saved in about a second. The chunks' embeddings are computed afterwards in the background (on a CPU about a second per chunk); until then those chunks are found by keyword search. Indexing cut off by a restart is finished at the next start.
- **Answers:** a short PDF (up to 5 chunks, e.g. a notice of a few pages) goes into the AI's context whole; a longer one is searched (keywords + meaning). A few website chunks are added too, so questions can mix the PDF with college information. Answers show chips such as "notice.pdf · page 2". The PDF is treated as the student's own document, not official college information.
- **Limits:** text PDFs only (scanned images have no text to read), `UPLOAD_MAX_MB` (default 10) and `UPLOAD_MAX_PAGES` (default 100), 20 uploads per student per hour. PDFs made from Word text boxes (one word per line) are joined back into sentences.

## LLM

The backend talks to any chat API that is OpenAI-compatible, set by three keys in `backend/.env`:

```
LLM_BASE_URL=https://api.groq.com/openai/v1   # for now: Groq
LLM_MODEL=openai/gpt-oss-120b
LLM_API_KEY=<key>
```

- **The plan:** a self-hosted model on the college DGX server (vLLM, Ollama or TGI all have this API). Switching is only a change of these keys; see [DEPLOYMENT.md](DEPLOYMENT.md#switching-to-the-college-dgx-llm). The old names `GROQ_API_KEY` / `GROQ_MODEL` still work.
- **Limits for now:** Groq's free tier allows about 8,000 tokens per minute for `openai/gpt-oss-120b`, roughly 3 questions per minute for the whole app. When that's exceeded, users see "The assistant is getting a lot of questions right now…".
- **If the LLM server can't be reached,** users see "The assistant is not available right now…" and `/health` reports `"llm": "unreachable"`.

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

## Testing

**Automated tests** (backend, ~120 tests, about 2–3 minutes):

```powershell
cd backend
pip install -r requirements-dev.txt
pytest
```

- **Separate database:** the tests use `college_ai_test` (your `DATABASE_URL` database name + `_test`, or `TEST_DATABASE_URL`), which is created and migrated automatically. They refuse to run on a database whose name doesn't end in `_test`, so your real data is safe.
- **No email, no AI:** email sending and the AI are stubbed, so no emails are sent and no LLM calls are made.
- **What's covered:**
  - signup/OTP rules, login, profile, password reset, rate limits, security headers
  - chats (incl. streaming, sources, and that one student can't see another's chats), guest chat, admin endpoints
  - crawler (on a saved real page), knowledge base, website sync safety rules, RAG source and language handling
  - PDF upload: upload/replace/remove, limits and bad files, privacy, background indexing and how the PDF is searched
- **Lint:** `ruff check .` (backend), `npm run lint` (frontend)

**Answer quality** (needs the backend running with the real knowledge base and LLM): asks 22 real questions (HODs, principal, fees, contacts, Hindi/Marathi/Hinglish…) and checks the facts:

```powershell
cd backend
python -m scripts.eval_answers            # 20 s pause between questions for Groq's free tier
python -m scripts.eval_answers --delay 0  # with a faster / self-hosted LLM
```

**CI:** `.github/workflows/ci.yml` runs the backend lint and tests (with a PostgreSQL service) plus the frontend lint and build on every push and pull request.

## Deployment

`docker compose up -d --build` runs PostgreSQL, the backend, Caddy (frontend + HTTPS) and a daily database backup on one server. Step-by-step guide (a free Oracle Cloud VM or a college server): [DEPLOYMENT.md](DEPLOYMENT.md).

`GET /health` reports the database, the knowledge base (number of chunks) and whether the LLM server answers. It returns 503 if the database or the knowledge base is down.

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
    routers/          API endpoints (auth, chat sessions, guest chat, password reset, admin, health)
    services/         business logic (auth, OTP, email, knowledge base, RAG,
                      website crawler + sync)
    schemas/          request/response models
  alembic/            database migrations
  college_data/       knowledge base text files
  scripts/            check_db.py, check_llm.py, build_index.py, eval_answers.py
  Dockerfile
frontend/
  src/
    components/       Auth, Chat, Layout, Sidebar
    context/, hooks/  auth state, chat sessions
    services/         API client
  Dockerfile, Caddyfile
docker-compose.yml    production setup (see DEPLOYMENT.md)
```

## Security

- Never commit `backend/.env`. It is git-ignored; `backend/.env.example` lists the keys without values.
- `JWT_SECRET` should be long and random: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- **Signup** is limited to `ALLOWED_SIGNUP_DOMAINS` (default `apsit.edu.in`) and needs an emailed OTP.
- **OTPs** are 6 random digits (`secrets`), stored only as an HMAC hash, valid 10–15 minutes, and stop working after 5 wrong guesses. Requesting a new code cancels the old one.
- **Passwords:** 8–128 characters with uppercase, lowercase and a number; hashed with argon2. A password reset logs out every other session.
- **Rate limits:** too many login, OTP or password-reset requests get `429 Too many attempts` (per email and per IP). Chat is not rate-limited.
- **API responses** carry security headers (`nosniff`, `X-Frame-Options: DENY`, ...).
- **In production:** set `ENABLE_DOCS=false`. Set `TRUST_PROXY_HEADERS=true` only behind a reverse proxy. `docker-compose.yml` does both.
- **The website crawler** only follows redirects within `www.apsit.edu.in`.
