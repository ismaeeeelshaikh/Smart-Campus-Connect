# APSIT College AI Assistant: Production Roadmap

This is the step-by-step plan for taking this project from "works on my laptop" to production-ready.
The phases are in dependency order: **finish each phase before starting the next**, because later phases build on earlier ones.
Tick each box as it's done.

| Phase | Goal | Why it comes here |
|---|---|---|
| 0 | Stop the credential leak | Urgent. Anyone on GitHub can use the leaked password right now |
| 1 | Clean repo + reproducible setup | Every later change needs a project that installs and runs from scratch |
| 2 | Fix broken features | Signup and some endpoints are broken today |
| 3 ✅ | Fix the RAG core + guest mode | Needed before adding live data, or the crawler has nowhere good to put it. Guest mode needs the new history handling. |
| 4 ✅ | Live website sync | **Sir's requirement:** changes on apsit.edu.in show up in the chatbot |
| 5 ✅ | Security hardening | Before real students use it |
| 6 ✅ | Frontend polish + redesign | Show sources, streaming, remove dead code |
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
- [x] **0.6** Put the new sending email's address and app password in `backend/.env` (`MAIL_USERNAME`, `MAIL_FROM`, `MAIL_PASSWORD`).
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

- [x] **2.1** Signup works: `VerifySignupOtp.jsx` now calls `/api/auth/complete-signup` (it was `/apiauth/...`). Errors show the backend's message instead of raw JSON.
- [x] **2.2** The OTP is deleted after a successful signup, so it can't be reused.
- [x] **2.3** Removed `POST /auth/register` (the no-OTP bypass), `authAPI.register`, the unused `register` in `AuthContext.jsx`, and the unused `hooks/useAuth.js`.
- [x] **2.4** Removed the old single-chat feature: backend router/service/schema/model, `User.chats`, frontend `useChat.js` + `chatAPI`, and the dead `Layout.jsx` + `Sidebar.jsx` that used them. Migration `4e0b41ddf85c` drops the `chats` table.
- [x] **2.5** One `get_current_user` in `app/dependencies.py`. It also returns 401 (not 404) if the token's account no longer exists.
- [x] **2.6** Renaming a chat uses the `ChatSessionTitleUpdate` schema (1–100 characters, trimmed). A bad body now returns 422 instead of 500.
- [x] **2.7** Password reset uses `utils/security.get_password_hash` (argon2), the same hasher as signup.
- [x] **2.8** No internal errors reach users: routers log the full error and return a generic message. Logging is configured once in `main.py` at INFO level (`routers/auth.py` had forced DEBUG for the whole app).
- [x] **2.9** Password reset returns 400 "Invalid or expired OTP" for a wrong OTP *and* for an unknown email, so it can't be used to discover accounts. Email-sending failures return a friendly 503 instead of a 500.

**Added during Phase 2:**
- [x] **2.10 College-email signup:** only `@apsit.edu.in` addresses can sign up (`ALLOWED_SIGNUP_DOMAINS` in `.env`); `ADMIN_EMAIL` is always allowed. The signup form shows the rule and the backend's reason on rejection. An already-registered email gets "Please log in" at the OTP step instead of after it.
- [x] **2.11 Wrong password no longer reloads the login page:** the axios interceptor treated every 401 as "session expired" and redirected, which wiped the error message. It now skips `/auth/*` requests.
- [x] **2.12 Header shows the real username:** `AuthContext.login` stored the part of the email before `@`; it now stores the `user` object the backend returns.
- [x] **2.13 Login shows "Account created! Please sign in."** after signup. Emails are lowercased everywhere, so login is case-insensitive.
- [x] **2.14 Default model is `openai/gpt-oss-120b`,** because Groq removed the Llama model.

**Verified on 2026-10-01:**
- **API:** 28/28 end-to-end checks passed (real DB; email and LLM stubbed): signup rules, OTP reuse, login, chat create/follow-up/rename/delete, 404/401/422 cases, the full password reset, and argon2 hashing.
- **Frontend:** `npm run build` passes.
- **Still to do (you):** try it in the browser with a real OTP email.

---

## Phase 3: Fix the RAG core + guest mode ✅

- [x] **3.1 The server isn't blocked any more.** The LLM call uses `await llm.ainvoke(...)`, and embedding/search run in `asyncio.to_thread`. *Verified:* two questions sent at once were both answered in ~4.4 s, and `/health` answered in ~0.01 s while they ran.
- [x] **3.2 No DB transaction is held during the LLM call.** A new chat gets its answer first, then writes the session + message in one short transaction. A follow-up reads its history, ends the read transaction, calls the LLM, then writes.
- [x] **3.3 Pickle memory removed.** `rag.answer(question, history)` takes the history as a parameter. Logged-in chats load the last 4 Q&A pairs from `chat_messages`, and guests send theirs from the browser. `conversation_memory.pkl` is deleted.
- [x] **3.4 Persistent knowledge base** (`app/services/knowledge_base.py`, folder `backend/chroma_db/`). Every document has a `source` id and a content hash, and only changed sources are re-embedded. Deleted files are removed from the index. Chroma telemetry is off. `python -m scripts.build_index [--rebuild]` rebuilds by hand. *Verified:* the first full index takes ~4.5 min; a restart with no changes takes **56 s** (was 4–5 min). The remaining time is Python importing torch/transformers on Windows (~35 s): the model loads in 0.7 s and a query embeds in 0.15 s.
- [x] **3.5 New retrieval:**
  - chunks of ~1000 characters, split by `=== SECTION ===`, each prefixed with the document title and section name
  - metadata `source` / `title` / `url` / `kind` on each chunk
  - **hybrid search:** vector search combined with BM25 keyword search (reciprocal rank fusion), so exact terms like "DTE code", names and abbreviations are found
  - follow-up questions are searched together with the previous question
  - `[cite_start]` / `[cite: …]` scraping leftovers are stripped (96 → 72 chunks)
  - *Verified:* for 12/12 test questions the right chunk ranks first; before, "DTE code" wasn't found
- [x] **3.6** `RAGService` is created in FastAPI's `lifespan` (`init_rag_service()`), not at import time. Tests replace it with `set_rag_service(stub)`.
- [x] **3.7 New prompt:**
  - a system message with rules
  - answers only from the context, and says so when the information isn't there (tested: "Who is the principal?" → "not in my information, see apsit.edu.in")
  - the context is treated as data, not instructions
  - declines off-topic requests
  - includes official links found in the context
  - greets only on the first message
- [x] **3.8** Removed the keyword HOD hack and the DuckDuckGo search, plus `langchain`, `langchain-community`, `duckduckgo_search` and `ddgs` from `requirements.txt`. The code now uses `chromadb` and `sentence-transformers` directly.
- [x] **3.9** The model name comes from `settings.groq_model` (done in Phase 1; default `openai/gpt-oss-120b`).
- [x] **3.10 Guest mode for newcomers.**
  - **Backend:** `POST /guest/chat` has no login, takes `{question, history}`, uses the same `answer()`, and saves nothing.
  - **Frontend:**
    - **"Chat as guest"** on the login page, plus a link under the signup email field
    - a public `/guest` page with a "Guest" header and a "not saved" banner
    - history kept in React state only
  - **No question limits** *(decision 2026-10-01)*. Questions are capped at 4000 characters and only the last 4 history turns are used; that's input validation, not a quota.
  - *Verified:* guest chats wrote 0 rows to the DB, and guest follow-ups work.

**Verified on 2026-10-01:**
- **API:** 36/36 checks passed (Phase 2 checks + history-from-DB + guest mode + 422 cases).
- **Real AI:**
  - correct HOD answers for IT and Civil
  - pronoun follow-ups work ("What is her qualification?" and "How many years of experience does he have?"); before, these got "not available"
  - DTE code found
  - no made-up principal name
  - off-topic request declined
- **Frontend:** `npm run build` passes.

**Not done yet (moved):**
- Answers mention official links when the context has them, but *structured* sources (a clickable list under each answer) need page URLs, which the crawler adds in **Phase 4**. The UI for them is **6.1**.
- The local data is stale: it says the Civil HOD has "36 years, pursuing PhD", while the live site says 17 years, PhD → **Phase 4**.
- *Optional for deployment:* replacing `sentence-transformers`/PyTorch with an ONNX runtime (e.g. `fastembed`) would cut startup time and ~1.5 GB of dependencies → consider in **Phase 8**.

---

## Phase 4: Live website sync (sir's requirement) ✅

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

### More facts found while building it (2026-10-01)
- **Size:** about 1,015 content pages plus ~340 linked PDFs.
  - **`/node/<id>` pages (~500):** events and webinars with dates, committee members and newsletters.
  - **~150 faculty profile pages:** interests, publications, roles.
  - **~150 pages** have almost no text.
- **Page content** is in `.region-content` on every page. The header, menu (2.3k characters), carousel, sidebars and footer repeat everywhere.
- **Some pages return HTTP 403** to every request (e.g. `/virtusa`, `/ayrus-academy-excellence-centre`). They're blocked by the site itself, not by us.
- **The site is inconsistent about the principal's email:** the principal page (`/node/41`) says `principal@apsit.edu.in`, the footer says `principal@apsit.org.in`.

### Steps
- [x] **4.1 Crawler** (`app/services/crawler.py`):
  - async `httpx` with browser headers
  - breadth-first crawl from `/` following every link, with 0.5 s between requests
  - URL normalisation (drops `/index.php`, `#fragment` and trailing `/`, keeps only `?page=`; other sites, images, `/user`, `/cdn-cgi` and similar are skipped)
  - duplicate pages (same text under two URLs) are indexed once
  - **downloads are streamed**, with a size cap (8 MB) and a 90 s time limit, plus 3 retries with back-off
- [x] **4.2 Extractors:**
  - text only from `.region-content`
  - **listing cards → one line each**, e.g. `Dr. Mugdha Agarwadkar | department: Civil Engineering | designation: Head of Department | qualification: PhD | experience: 17 years | profile: …`
  - Cloudflare-hidden emails decoded
  - footer contact details indexed **once** as their own document (`/#contact`)
  - links to PDFs are kept in the page text with their URL, so the bot can point to documents it hasn't read
- [x] **4.3 Tables:**
  - `crawled_pages`: url, title, kind, status, first_seen / last_crawled / last_changed
  - `crawl_runs`: status and counters for each sync
  - timezone-aware timestamps; migration `a57c0199b0e2`
- [x] **4.4 Incremental sync** (`app/services/website_sync.py`):
  - only pages whose text hash changed are re-embedded
  - 404s are removed
  - pages that weren't visited are removed **only if** the crawl didn't hit the page limit and reached ≥ 80% of the previous run
  - a sync that reads 0 pages is marked failed and removes nothing
  - one sync at a time (lock)
  - runs cut off by a restart are marked "interrupted" at startup
- [x] **4.5 PDFs:**
  - content of the **60 newest** PDFs (by Drupal's `/files/YYYY-MM/` folder), first 25 pages / 40k characters each
  - scanned PDFs (no text) are skipped
  - **merit lists / student lists are never read** (filename filter), to protect students' personal data
- [x] **4.6 Scheduler:**
  - an asyncio background task (no extra dependency) checks every 10 min and syncs when the last success is older than `CRAWL_INTERVAL_HOURS` (default 6; 0 = off)
  - the first sync starts ~15 s after the very first startup
- [x] **4.7 Admin API** (admins = `ADMIN_EMAIL`, comma-separated):
  - `POST /admin/website-sync` starts a full sync in the background (409 if one is running)
  - `GET /admin/website-sync` returns progress, last run, pages indexed and the 10 most recently changed pages
  - `POST /admin/website-sync/page {url}` **re-reads one page in seconds** (the demo button)
  - non-admins get 403
  - the login response includes `is_admin`
- [x] **4.8 Admin UI:** a **"Website sync"** button in the header, for admins only. It opens a panel with:
  - **Sync now**, with live progress
  - **Update one page** (paste a URL)
  - the last result
  - recently changed pages (with links)
- [x] **4.9 Manual data:**
  - deleted `faculty_all_departments.txt` (stale; all 7 faculty pages are now read live)
  - removed the "Department Leadership" lines from `IT_Teachers.txt` (stale, and they contained the HOD's personal mobile number); its teaching assignments stay because they're not on the website
  - context entries are labelled "official APSIT website page: <url>" or "college data file", and the prompt says **the website wins** when they disagree
  - answers end with "Source:" links to the pages used; `【1】`-style markers are stripped

**Verified on 2026-10-01:**
- **First full sync:** 1,046 pages/PDFs, 1,001 indexed, 36 failed (the 403 pages), 2,591 chunks. It took ~45 min of crawling + embedding; a 72-min pause in the log was the laptop sleeping.
- **Re-sync:** the same pages found **unchanged in 39 s** with nothing re-embedded.
- **Responsiveness:** chat answered in ~1.5 s *while* a sync was running.
- **Simulated demo:**
  - the index held an "old website" version of `/tpo` → the bot said "Prof. Test Person"
  - admin "Update one page" → `updated`
  - the bot then said "**Prof. Sushrut Patankar**" with the source link, and the panel listed `/tpo` as recently changed
- **Live data:**
  - the Civil HOD is now correct (PhD, 17 years; was "36 years, pursuing PhD")
  - the IT HOD shows 21 years
  - the principal **Dr. Uttam D. Kolekar** is found (the old data didn't have it)
  - CAP-vacancy admission dates come from the home page
  - faculty research interests and events with dates are answered
- **API:** 49/49 checks pass (earlier phases + admin permissions + crawler unit checks).

**Demo script for sir:**
1. Log in with an admin account and ask: "Who is the HOD of Civil Engineering?" The answer shows the live data and a link to `/civil-faculty`.
2. Sir edits a page on apsit.edu.in, for example a faculty card.
3. Open **Website sync** → paste that page's link into **Update one page** → it says "Changes found and updated".
4. Ask again. The answer shows the new information. (Without pressing anything, the automatic sync picks the change up within 6 hours.)

**Known limits / later:**
- **The "Source:" line is written by the AI,** so it can occasionally cite a related page instead of the exact one → **6.1** builds the source list from retrieval results instead.
- **Scanned PDFs and text inside images** aren't read (that would need OCR).
- **A full sync takes ~20 min of polite crawling** even when nothing changed. That's fine every 6 h; a smarter order (recently changed pages first) could come later.

---

## Phase 5: Security hardening ✅

- [x] **5.1 Rate limits** (`app/utils/rate_limit.py`, in memory, no extra package):
  - **Login:** 10 tries per email and 20 per IP, per 15 min.
  - **Signup OTP request:** 3 per email per 15 min, 10 per IP per hour.
  - **OTP verify:** 10 per email per 15 min.
  - **Reset OTP request:** 3 per email per 15 min, 10 per IP per hour.
  - **Reset verify:** 10 per email per 15 min.
  - Over the limit → **429** "Too many attempts. Please try again in N minutes." with a `Retry-After` header.
  - **Chat (logged-in and guest) is not limited** (decision 2026-10-01).
  - Behind a reverse proxy set `TRUST_PROXY_HEADERS=true` so the real client IP is used.
  - Limits reset on restart and aren't shared between several worker processes (see Phase 8).
- [x] **5.2 OTPs:**
  - generated with `secrets` (not `random`)
  - stored only as an **HMAC hash** with the server secret, so a leaked database can't be brute-forced
  - **5 wrong guesses kill the code**
  - requesting a new code cancels the old one (signup and reset)
  - a reset code can't be used twice
  - migration `61b787cb4910` deleted the old plain-text OTP rows
- [x] **5.3 Validation:**
  - **new passwords:** 8-128 characters with an uppercase letter, a lowercase letter and a number (same rule in the backend schemas and the frontend, `services/validation.js`)
  - **usernames:** 3-30 of letters, numbers, `.` `_` `-`
  - **OTP:** exactly 6 digits
  - **size limits:** login password ≤ 128 characters (stops huge inputs that are slow to hash); guest history ≤ 50 turns; questions ≤ 4000 characters
- [x] **5.4 JWT:**
  - timezone-aware expiry, plus an `iat` (issued-at) claim
  - **a password reset logs out every other session:** `users.password_changed_at` makes older tokens invalid
  - admin check in a dependency (done in Phase 4)
  - a 401 on login no longer reloads the page (done in Phase 2)
- [x] **5.5 Security headers on every API response:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`. CORS origins come from settings (done in Phase 1). HSTS/HTTPS belongs to the web server in **Phase 8**.
- [x] **5.6** `/docs`, `/redoc` and `/openapi.json` can be turned off with `ENABLE_DOCS=false`. Keep them on in development; turn them off in production.
- [x] **5.7 Crawler can't be redirected away:** redirects are followed by hand, only within `www.apsit.edu.in`, so a redirect can't make the server request another site or an internal address (SSRF) or index foreign content.

**Verified on 2026-10-01:**
- **70/70 API checks pass**, including all the new ones:
  - OTP stored hashed
  - after 5 wrong OTPs even the right one fails
  - a new OTP cancels the old one
  - weak password / bad username / non-numeric OTP → 422
  - the 11th login try → 429 while another email can still log in
  - the 4th OTP request → 429
  - **old token → 401 after a password reset**, new token works
  - reset OTP single-use
  - security headers present
  - an off-site redirect is not followed
- **Live server:** headers present; the user's `@apsit.edu.in` account is admin.

**Lesson:** `uvicorn --reload` on Windows got stuck after a `.env` change (the old process kept running), so run the backend without `--reload` and restart it after editing `.env`.

---

## Phase 6: Frontend polish + redesign ✅

- [x] **6.1 Source chips under each answer.**
  - `rag.finalize_answer()` turns the model's trailing "Source:" block (and inline links) into a `sources` list, **keeping only URLs that were in the retrieved context**, so invented or foreign links are dropped. The "Source:" text is removed from the answer.
  - Sources are saved in `chat_messages.sources` (JSON, migration `f19fd24435ac`) and returned by every chat and guest endpoint.
  - The UI shows them as chips (PDFs get a document icon).
- [x] **6.2 Streaming answers (server-sent events):**
  - endpoints: `POST /chat-sessions/start/stream`, `POST /chat-sessions/{id}/messages/stream`, `POST /guest/chat/stream`
  - events: `token`, then `done` (saved message/session + sources), or `error` with a friendly message
  - the message is saved after the stream completes, using its own DB session
  - frontend: `services/stream.js` reads the stream with `fetch`; typing dots until the first word, then a blinking caret
- [x] **6.3** `VITE_API_URL` (`src/services/config.js`, `frontend/.env.example`) is used by axios and the stream client. Signup/OTP pages now use the shared API client instead of hard-coded `fetch('/api/...')`.
- [x] **6.4 ESLint 9** with flat config (`eslint.config.js`: React, hooks, refresh). `npm run lint` → 0 errors, 1 harmless warning (`AuthContext.jsx` exports a hook next to the provider; it only affects dev hot reload). Two "setState in effect" errors were fixed by loading data in a promise callback / click handler.
- [x] **6.5 States:**
  - **Errors:** "Can't reach the server…" for network errors; chat errors offer **Try again**.
  - **Loading:** skeleton rows while chats load, "Opening chat…" when switching chats, and an empty-state message when there are no chats.
  - **Login:** wrong password keeps its message; 429 messages are shown as is.
- [x] **6.6** One auth source (`AuthContext`); the duplicate `useAuth.js` was removed in Phase 2.

**Redesign ("APSIT Heritage")**
- **Brand:** colours from the college crest: teal `#145C5F`, gold `#E0A91B`, crimson `#A51D2D` on paper `#F7F4EC`. No purple/neon "AI app" look. Literata (serif) + Hanken Grotesk, bundled with `@fontsource` (no Google Fonts request). Concepts drafted in Google Stitch, then built in React/Tailwind with real content only (Stitch's invented names, links and "attendance" features were left out).
- **Auth pages** (sign in, sign up, OTP, forgot/reset password) share `AuthLayout`:
  - a teal brand panel with the real crest and three honest feature points
  - a form card with icon inputs, a show/hide password toggle, and inline errors (no more `alert()` popups)
- **Chat:**
  - **Sidebar:** white, with the crest wordmark, "New chat", recent chats (relative time, gold bar on the active one, rename and inline delete confirmation), and a user card with sign-out at the bottom.
  - **Top bar:** chat title + the admin "Website sync" button (restyled panel).
  - **Welcome screen:** crest, greeting with the user's name, and 4 suggestion cards.
  - **Messages:** teal user bubbles; white answer cards with crest avatar, markdown with tables (`remark-gfm`), gold bullets, source chips and a copy button.
  - **Composer:** grows with the text; Enter sends, Shift+Enter adds a new line; mic button.
- **Guest page:** same chat with a "Guest" header and a "not saved" notice.
- **Mobile:** the sidebar becomes a drawer, the header is compact, and there's a short placeholder.
- **Voice input** rewritten as `useSpeechInput`: the microphone permission is asked **only when the mic is pressed** (it used to be on every page load), and it restarts after pauses.
- **Clean-up:** `react-linkify` removed; `lucide-react` updated 0.294 → 1.49; `.env.*` git-ignored (`frontend/.env.production` would have been committed).

**Verified on 2026-10-01:**
- **API:** 81/81 checks (earlier phases + sources saved/returned, streamed new chat and follow-up saved with history, 404/401 on streams, guest stream, a failing stream → friendly `error` event).
- **Frontend:** `npm run build` and `npm run lint` (0 errors) pass.
- **Screenshots in Edge (Playwright), desktop + mobile:**
  - login and register (inline validation)
  - guest welcome, streaming and answer (real AI: "Dr. Mugdha Agarwadkar, 17 years", chip "Civil Faculty")
  - student welcome and conversation (streamed follow-up, gold bullets, chips)
  - mobile guest answer ("Dr. Uttam D. Kolekar", chip "About Us") and mobile drawer
- **Bugs found and fixed during the screenshots:** a gold focus ring showed inside text inputs; mobile header wrapping; the welcome screen scrolled itself to the bottom; a long placeholder made the composer 3 lines tall on mobile.

**Not done / ideas:**
- a "Stop generating" button
- a dark mode
- the "Source:" chips depend on the model citing pages; if it cites nothing, no chips are shown

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
| 2026-10-01 | Phase 2 | Broken features fixed, college-email-only signup; 28/28 API checks pass |
| 2026-10-01 | Plan change | Added 3.10 guest mode for newcomers, with no chat limits (Groq credits handled separately) |
| 2026-10-01 | Phase 3 | Async RAG, persistent hybrid-search index, DB history, new prompt, guest mode; 36/36 API checks pass |
| 2026-10-01 | Phase 4 | Live website sync: crawler, incremental index, scheduler, admin panel + single-page update; 1,046 pages indexed; 49/49 checks + demo pass |
| 2026-10-01 | Phase 5 | Rate limits, hashed OTPs with attempt limits, password rules, sessions revoked on password reset, security headers; 70/70 checks pass |
| 2026-10-01 | Phase 6 | APSIT Heritage redesign (Stitch concepts), streaming answers, source chips, VITE_API_URL, ESLint, error states; 81/81 API checks |
