# APSIT College AI Assistant: Production Roadmap

This is the step-by-step plan for taking this project from "works on my laptop" to production-ready.
The phases are in dependency order: **finish each phase before starting the next**, because later phases build on earlier ones.
Tick each box as it's done.

| Phase | Goal | Why it comes here |
|---|---|---|
| 0 | Stop the credential leak | Urgent. Anyone on GitHub can use the leaked password right now |
| 1 | Clean repo + reproducible setup | Every later change needs a project that installs and runs from scratch |
| 2 | Fix broken features | Signup and some endpoints are broken today |
| 3 | Fix the RAG core | Needed before adding live data, or the crawler has nowhere good to put it |
| 4 | Live website sync | **Sir's requirement:** changes on apsit.edu.in show up in the chatbot |
| 5 | Security hardening | Before real students use it |
| 6 | Frontend polish | Show sources, streaming, remove dead code |
| 7 | Tests + CI | Keep everything working as we change things |
| 8 | Deployment | Put it online |

---

## Phase 0: Stop the credential leak ✅

A Gmail app password was hardcoded in `email.py` and `password_reset.py` and pushed to the old public repo.

- [x] **0.1** Revoked the leaked Gmail app password; deleted the old GitHub repo.
- [x] **0.2** Mail settings are now read only from `backend/.env`. `email.py` holds the one shared `ConnectionConfig` (built from `settings`), and `password_reset.py` reuses it.
- [x] **0.3** Removed the stray root-level `env` file.
- [x] **0.4** The DB URL now comes from `.env` everywhere: `alembic/env.py` sets it from `settings`, and `test_db_connection.py` / `test_groq.py` read `settings`.
- [x] **0.5** Expanded `.gitignore` (secrets, `*.pkl`, Chroma folders, `temp_uploads/` with personal data, venv, node_modules, dist). Added `backend/.env.example`.
- [ ] **0.6** Put the new sending email's address and app password in `backend/.env` (`MAIL_USERNAME`, `MAIL_FROM`, `MAIL_PASSWORD`). *(You)*
- [x] **0.7** Pushed to the new repo `Smart-Campus-Connect` with a fresh git history.

**Checked:** a simulated fresh `git add .` stages 86 files, and none of them contains a password, API key or personal phone number.

---

## Phase 1: Clean repo + reproducible setup

Right now a fresh clone **cannot** be set up: the migrations are broken and `requirements.txt` is saved in UTF-16.

### 1A. Remove junk from git
- [x] **1.1** `backend/temp_uploads/` (44 MB of PDFs), `backend/*.pkl`, `backend/chroma_db_final/` and `backend/memory_vectorstore/` are git-ignored, so the fresh history won't include them.
- [x] **1.2** Deleted dead code: `backend/app/utils/advanced_rag_utils.py` (260 lines, all commented out) and `frontend/src/components/Sidebar/ChatHistory.jsx` (empty).
- [x] **1.3** Moved the check scripts to `backend/scripts/check_db.py` and `check_groq.py` (run with `python -m scripts.check_db`). Named `check_*`, not `test_*`, so pytest won't collect them in Phase 7. Replaced their emojis, which crash on the Windows console.

### 1B. Dependencies and config
- [x] **1.4** `requirements.txt` is now UTF-8 with 23 direct dependencies instead of 170 pinned packages; pip resolves the rest. Python **3.12** (3.13+ isn't supported by all ML packages yet). `pip check` passes.
- [x] **1.5** `config.py` is the single source of config: added `groq_model` and `cors_origins`, and `rag.py` / `main.py` read from `settings` (no more `os.getenv` / `load_dotenv`). `.env` is found from any working directory. *(`chroma_dir`, `embedding_model` and `crawl_interval_hours` will be added in Phases 3–4 when they're used.)*
- [x] **1.6** Add `backend/.env.example` with every key and no values.
- [x] **1.7** Removed `echo=True` from `database.py`.

### 1C. Fix the database migrations
Current state of the migration chain `d5da47b3c6e1 → df824e25ef7a → ead537a66732 → 975eed345791`:
- two migrations are empty (`pass`)
- `975eed345791` is named "add password reset tokens" but actually **drops** `chat_sessions` and `chat_messages`, and never creates `password_reset_tokens`
- `alembic/env.py` imports only `user` and `chat`, so autogenerate can't see the other models
- `signup_otp_token.py` defines its **own** `Base`, so Alembic never sees that table
- nothing creates `chat_sessions`, `chat_messages`, `password_reset_tokens` or `signup_otp_tokens`

- [x] **1.8** `signup_otp_token.py` now uses the shared `Base`.
- [x] **1.9** `app/models/__init__.py` imports every model, and `alembic/env.py` imports that package.
- [x] **1.10** Replaced the 4 broken migrations with one clean migration, `89edb413fa81_initial_schema`: 6 tables, plus indexes on `chat_sessions.user_id`, `chat_messages.chat_session_id` and `chat_messages.user_id`. Verified: `alembic check` finds no difference between models and DB, and downgrade → upgrade works.
- [x] **1.11** The old `college_ai` database no longer existed on this PostgreSQL 18 install, so a fresh one was created with `alembic upgrade head`. There was no data to migrate.

### 1D. Docs
- [x] **1.12** Rewrote `README.md` with the exact Windows setup steps, requirements, migrations workflow and project structure.

**Verified on 2026-10-01:**
- **Backend:** the backend starts, and `/health` responds.
- **Full API flow:** register → login → start chat → follow-up → list → delete all work. A chat answer takes about 11 s.
- **Frontend:** `npm install` + `npm run build` succeed.
- **Not tested yet:** the OTP email, because `.env` still has the old mail account.

**Found during testing (fixed in later phases):**
- Backend startup takes several minutes, because the whole knowledge base is re-embedded on every start → 3.4
- The follow-up "What is her qualification?" (about the Civil HOD) got "not available"; the live site says PhD → Phase 4
- `logging.basicConfig(level=logging.DEBUG)` in `routers/auth.py` makes the whole app log at DEBUG level → 2.8
- Chroma sends anonymous telemetry to posthog.com by default; turn it off with `anonymized_telemetry=False` → 3.4
- The old `POST /chat` returns 500 as expected → 2.4

---

## Phase 2: Fix broken features

- [ ] **2.1 Signup is broken:** `frontend/src/components/Auth/VerifySignupOtp.jsx:31` calls `/apiauth/complete-signup`. Change it to `/api/auth/complete-signup`.
- [ ] **2.2** Delete the OTP after a successful signup; right now it can be reused until it expires.
- [ ] **2.3** Remove `POST /auth/register`. It creates users **without** OTP verification. Remove the matching `authAPI.register` in the frontend and the duplicate `register` logic in `useAuth.js` / `AuthContext.jsx`.
- [ ] **2.4** Remove the old single-chat feature, which is always broken: `routers/chat.py`, `services/chat.py`, `schemas/chat.py`, the `Chat` model and `User.chats`. `ChatService.create_chat` calls `rag_service.get_response()`, which doesn't exist. Also remove frontend `useChat.js` and `chatAPI` (including `DELETE /chat/clear`, which never existed). Add a migration that drops the `chats` table.
- [ ] **2.5** Move the duplicated `get_current_user` into `app/dependencies.py` and use it in every router.
- [ ] **2.6** `PUT /chat-sessions/{id}/title` accepts a raw `dict`. Use a Pydantic schema (`title: str`, 1–100 characters).
- [ ] **2.7** Use one password hasher everywhere: `password_reset.py` makes its own bcrypt-only `CryptContext`; use `utils/security.get_password_hash` instead.
- [ ] **2.8** Stop sending internal errors to users (`detail=str(e)` in every router). Log the full error on the server and return a generic message.
- [ ] **2.9** Password reset: the service raises a bare `Exception` for "user not found" or "invalid OTP", which becomes a 500. Return a 400 with a clear message instead.

**Done when:** signup (with OTP) → login → new chat → follow-up message → rename → delete → forgot password all work in the browser without errors.

---

## Phase 3: Fix the RAG core

- [ ] **3.1 Stop blocking the server.** `rag_service.get_response_for_session` runs synchronous LLM, embedding and search calls inside `async` routes, so one slow answer freezes every user. Use `await llm.ainvoke(...)` / `await asyncio.to_thread(...)`.
- [ ] **3.2 Don't hold a DB transaction open during the LLM call.** `create_session_with_first_message` does `flush()`, then waits for the LLM, then commits. Get the answer first, then write both rows in one short transaction.
- [ ] **3.3 Remove the pickle memory** (`conversation_memory.pkl`). It duplicates the `chat_messages` table, is rewritten after every message and grows forever. Load the last 6 messages of the session from the DB instead. Delete `_load/_save_conversation_memory` and `clear_session_memory`.
- [ ] **3.4 Stop wiping the vector DB on startup.** `_load_or_create_retriever` runs `shutil.rmtree("./chroma_db_final")` and re-embeds everything on every start. Keep Chroma persistent; build or update it with a separate command (`python -m app.scripts.build_index`) and later with the crawler (Phase 4).
- [ ] **3.5** Replace `ParentDocumentRetriever` + `InMemoryStore`: the in-memory parent store is lost on restart and doesn't match a persistent vector store. Use a plain Chroma retriever with ~1000-character chunks and `source` / `title` / `crawled_at` metadata on every chunk.
- [ ] **3.6** Create `RAGService` in FastAPI's `lifespan` instead of at import time (`rag_service = RAGService()` at the bottom of `rag.py`). Right now even `alembic` or a test import loads the embedding model.
- [ ] **3.7 Rewrite the prompt:**
  - use a proper system message plus the user message
  - answer only from the provided context; say "I don't know" when the answer isn't there
  - end each answer with the source link(s)
  - treat website text as data, not instructions
  - remove the "web search is the TRUTH" rule
- [ ] **3.8** Remove the keyword HOD hack (`"it" in q_lower` also matches "institute" and "with") and the DuckDuckGo search. Phase 4 replaces both with real website data.
- [ ] **3.9** Read the model name from `settings.groq_model` instead of the hardcoded `"llama-3.3-70b-versatile"`.

**Done when:** two browser windows can chat at the same time without waiting on each other, a backend restart takes seconds, and every answer ends with its source.

---

## Phase 4: Live website sync (sir's requirement)

**Goal:** when anything changes on https://www.apsit.edu.in, the chatbot's answer changes too, at the next scheduled crawl or immediately when an admin presses **Refresh**.

### Verified facts about apsit.edu.in (tested 2026-09-28)
- **Platform:** Drupal 10, server-rendered HTML, so no headless browser is needed.
- **Firewall:** Cloudflare + ModSecurity return **406** for plain scripts. Requests work with normal browser headers (`User-Agent`, `Accept`, `Accept-Language`).
- **Discovery:** there's no `sitemap.xml` (404), but `/rss.xml` exists. Pages have to be found by following links.
- **Change detection:** there's no `Last-Modified` or `ETag` header (`Cache-Control: no-cache`), so change detection has to hash each page's content.
- **Faculty pages:** each is a grid of `article[data-history-node-id]` cards with the fields `field--name-field-department`, `-designation`, `-qualification` and `-year-of-passing` (experience). There's no pagination.
- **Faculty page URLs:** `/computer-faculty`, `/civil-faculty`, `/mechanical-faculty`, `/Information-faculty`, `/data-science-faculty`, `/aiml-faculty`, `/has-faculty`. The prototype parsed all 7 HODs and 153 cards correctly.
- **Emails:** hidden by Cloudflare as `/cdn-cgi/l/email-protection#<hex>` and decodable with a simple XOR.
- **Boilerplate:** a carousel ("Convocation Ceremony @APSIT…") and the footer repeat on every page and must be stripped.
- **Proof the old data is stale:** the scraped files say 20 and 23 years of experience for the IT and Humanities HODs; the live site says 21 and 24.

### Steps
- [ ] **4.1 Crawler** (`app/services/crawler.py`):
  - async `httpx` with browser headers
  - breadth-first crawl of `www.apsit.edu.in` starting from `/` and `/rss.xml`
  - normalise URLs (drop `/index.php/` and `#fragment`)
  - skip images, video and zip files
  - 0.5 s delay between requests
  - `max_pages` limit
  - retry with back-off on errors
- [ ] **4.2 Extractors:**
  - *Faculty-card extractor:* turn each card into one sentence, e.g. "Dr. Kiran B. Deshpande is the Head of Department of Information Technology (PhD, 21 years experience)."
  - *Generic extractor:* page text without nav, header, footer or carousel.
  - *Email decoder* for Cloudflare-protected addresses.
- [ ] **4.3 Page state table** `crawled_pages(url, title, content_hash, last_crawled, last_changed, status)`, with an Alembic migration.
- [ ] **4.4 Incremental sync:**
  - hash unchanged → skip
  - hash changed → delete that URL's chunks in Chroma and add the new ones
  - page gone → delete its chunks, **but only if the crawl finished normally** (e.g. reached ≥ 80% of the last crawl's page count), so a network failure can't wipe the knowledge base
- [ ] **4.5 PDFs:** extract text from linked PDFs under `/sites/default/files/` with `pypdf`, with a size limit. Scanned PDFs and poster images would need OCR; leave that out of scope for now and document it.
- [ ] **4.6 Scheduler:** APScheduler started in `lifespan`, every `crawl_interval_hours` (default 6), with a lock so two crawls never overlap.
- [ ] **4.7 Admin API:**
  - admin = the user whose email matches `settings.admin_email`
  - `POST /admin/reindex` starts a crawl in the background
  - `GET /admin/crawl-status` returns the last run time, pages seen / changed / failed, and whether a crawl is running
- [ ] **4.8 Admin UI:** a **Refresh website data** button plus "last synced" time, visible only to the admin.
- [ ] **4.9 Manual data:** keep `college_data/*.txt` for information that isn't on the website, with source `manual:<file>`. Remove anything the crawler now covers (the faculty files) so old data can't contradict live data.

**Done when (demo script for sir):**
1. Ask "Who is the HOD of IT?" and get the live answer with a link to `/Information-faculty`.
2. Sir changes a page on the website.
3. Press **Refresh** and wait for the status to show "changed: 1".
4. Ask again. The answer shows the new information and the new "updated on" time.

---

## Phase 5: Security hardening

- [ ] **5.1** Rate limiting with `slowapi`: login, OTP request, OTP verify, password reset and chat. For example, at most 5 OTP requests per email per hour.
- [ ] **5.2 OTPs:**
  - generate with `secrets` instead of `random`
  - store a **hash** of the OTP, not the plain code
  - allow at most 5 wrong attempts, then invalidate
  - allow only one active reset OTP per user
- [ ] **5.3** Validation in the schemas: minimum password length (8), username pattern, maximum question length (e.g. 1000 characters).
- [ ] **5.4 JWT:**
  - use timezone-aware expiry times (`datetime.utcnow()` is deprecated)
  - put an `is_admin` claim or check in a dependency
  - frontend: on 401, clear the session and send the user to login without a redirect loop
- [ ] **5.5** Read CORS origins from settings. Add basic security headers.
- [ ] **5.6** Keep `/docs` (Swagger) only in development, or protect it.

**Done when:** brute-forcing an OTP or spamming login gets a 429, and no secret or stack trace ever reaches the browser.

---

## Phase 6: Frontend polish

- [ ] **6.1** Show sources under each bot answer as clickable links (the backend returns `sources: [{url, title}]`).
- [ ] **6.2** Streaming answers with server-sent events, so text appears while it's generated. Optional, but a big UX win.
- [ ] **6.3** Read the API base URL from `VITE_API_URL` so the production build works without the Vite dev proxy.
- [ ] **6.4** ESLint: the `lint` script exists but `eslint` isn't installed. Install it and fix the warnings.
- [ ] **6.5** Proper loading, empty and error states. Show a friendly message when the backend is down.
- [ ] **6.6** Use one auth source (`AuthContext`) and remove the duplicate `useAuth.js` logic.

---

## Phase 7: Tests + CI

- [ ] **7.1 Backend tests** with `pytest` + `httpx.AsyncClient` against a test DB: signup/OTP, login, sessions CRUD, admin permissions, and that one user can't read another user's session.
- [ ] **7.2 Crawler tests** with saved HTML fixtures (e.g. `Information-faculty.html`): the parser finds the HOD, the email decoder works, boilerplate is stripped, and an unchanged page is skipped.
- [ ] **7.3 Answer-quality check:** 20–30 real questions (HODs, fees, admission, placements, links) with expected facts. Run it after each crawl to catch regressions.
- [ ] **7.4** `ruff` for Python and `eslint` for React, plus a GitHub Actions workflow that runs lint and tests on every push.

---

## Phase 8: Deployment

- [ ] **8.1** Dockerfile for the backend (download the embedding model at build time) and for the frontend (`npm run build` served by nginx), plus `docker-compose.yml` with postgres + backend + frontend, and volumes for Postgres and Chroma.
- [ ] **8.2** Run the crawler scheduler in **one** process only: a separate `worker` service, or a DB lock if you run several uvicorn workers.
- [ ] **8.3** Make `/health` check the DB, Chroma and Groq. Use structured logs. Email the admin when a crawl fails.
- [ ] **8.4** Daily Postgres backups. Chroma doesn't need backups, since the crawler can rebuild it.
- [ ] **8.5** Hosting: a small VPS or Render/Railway with ≥ 2 GB RAM (the bge-base embedding model needs ~1 GB), HTTPS via the platform or Caddy/nginx + Let's Encrypt.

**Done when:** the app runs at a public HTTPS URL, survives a restart without losing data, and the crawler updates it on schedule.

---

## Progress log

| Date | Step | Notes |
|---|---|---|
| 2026-09-30 | Roadmap written | Analysis + live site tests done |
| 2026-09-30 | Phase 0 (code side) | Secrets moved to `.env`, `.gitignore` fixed, `.env.example` added |
| 2026-09-30 | Pushed to new repo | `Smart-Campus-Connect`, fresh history |
| 2026-10-01 | Phase 1 | Clean setup: requirements, config, migrations, README; tested end-to-end |
