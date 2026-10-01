# Deployment

How to run Smart Campus Connect on a server with Docker. The same setup works on a free Oracle Cloud VM (for now) and on a college server (later, next to the DGX LLM).

## What runs

`docker compose up` starts four containers on one machine:

| Container | What it does |
|---|---|
| `db` | PostgreSQL: users, chats, website-sync history. Data in the `pgdata` volume. |
| `backend` | FastAPI app with the embedding model. Knowledge base in the `chroma` volume. Syncs with apsit.edu.in every 6 hours. |
| `web` | Caddy: serves the React app, forwards `/api/*` to the backend, and gets a free HTTPS certificate for your domain. |
| `backup` | Dumps the database into `./backups` once a day and keeps 14 days. |

The LLM is not part of this setup. It's an outside OpenAI-compatible API: Groq for now, the college DGX server later (see [Switching to the college DGX LLM](#switching-to-the-college-dgx-llm)).

**Server needs:**
- 2+ CPU cores, 4+ GB RAM (the backend alone uses about 1.5–2 GB), 30+ GB disk
- Linux with Docker
- ports 80 and 443 open to the internet
- outgoing access to apsit.edu.in, the LLM API and the mail server (SMTP port 587)

## 1. Get a server

### Option A: Oracle Cloud Always Free (for now)

Free with no time limit: an ARM VM with 2 cores and 12 GB RAM, and up to 200 GB disk.

1. **Sign up** at https://www.oracle.com/cloud/free/.
   - Pick **Mumbai** or **Hyderabad** as the home region. It can't be changed later.
   - A card is needed for verification. Nothing is charged.
2. **Upgrade to Pay As You Go (recommended):** Billing → Upgrade.
   - Always Free resources stay free.
   - Free-tier-only accounts can lose a VM that looks idle for 7 days.
   - Set a budget alert (Billing → Budgets) so any accidental cost is caught.
3. **Create the VM:** Compute → Instances → Create instance.
   - **Image:** Canonical Ubuntu 24.04.
   - **Shape:** Ampere `VM.Standard.A1.Flex` with 2 OCPUs and 12 GB memory.
   - **SSH keys:** download the private key and keep it safe.
   - **Boot volume:** 50–100 GB.
   - If you get "Out of capacity", try another availability domain, or try again later.
4. **Open ports 80 and 443 in Oracle's firewall:** Networking → Virtual cloud networks → your VCN → Security Lists → Default.
   - Add ingress rules for TCP **80** and **443** from `0.0.0.0/0`.
   - Optionally add UDP 443 too (HTTP/3).
5. **Log in and open the same ports in the VM's own firewall.** Oracle's Ubuntu images block them by default:
   ```bash
   ssh -i oracle-key.pem ubuntu@<public-ip>
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
   sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```
6. **Install Docker**, then log out and back in:
   ```bash
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER
   ```

### Option B: a college server (final)

Any Linux machine or VM with Docker, ideally on the same network as the DGX server. Ask the college IT department for:

- **A machine:** a VM with 2+ cores, 4+ GB RAM and 30+ GB disk.
- **A name:** for example `chatbot.apsit.edu.in`, pointing to its public IP, with ports 80 and 443 open.
- **If there's no public IP:** a [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) can publish the site without one. In that case set `SITE_ADDRESS=:80` and let the tunnel provide HTTPS.

Then continue with step 3.

## 2. Get a domain name

HTTPS needs a domain. Free option:

1. Log in at https://www.duckdns.org.
2. Create a subdomain, e.g. `apsit-chat`.
3. Set its IP to the server's public IP.

The site is then `https://apsit-chat.duckdns.org`. With a college subdomain, skip this step.

## 3. Install and start the app

```bash
git clone https://github.com/ismaeeeelshaikh/Smart-Campus-Connect.git
cd Smart-Campus-Connect

cp .env.example .env                    # docker settings
nano .env
cp backend/.env.example backend/.env    # app settings
nano backend/.env

docker compose up -d --build
```

**`.env`** (next to `docker-compose.yml`):

| Key | Value |
|---|---|
| `POSTGRES_PASSWORD` | a new random password: `python3 -c "import secrets; print(secrets.token_urlsafe(24))"` |
| `SITE_ADDRESS` | your domain, e.g. `apsit-chat.duckdns.org` (Caddy then turns on HTTPS by itself), or `:80` for a first test over plain HTTP |

**`backend/.env`:** fill it in as for local development, with these differences:

- **`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`:** Groq for now (the defaults in `.env.example` plus your key).
- **`JWT_SECRET`:** generate a **new** one for the server: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **`ADMIN_EMAIL` and `MAIL_*`:** as locally.
- **Leave as they are:** `DATABASE_URL`, `TRUST_PROXY_HEADERS` and `ENABLE_DOCS` are set by `docker-compose.yml`. `CORS_ORIGINS` isn't needed, because the app and the API share one domain.

**What happens on the first start:**
1. **Image build:** 10–20 minutes. It downloads PyTorch and the embedding model.
2. **Backend start:** about 2 minutes. Database tables are created and the `college_data/` files are indexed.
3. **First website sync:** starts automatically and takes about an hour. Until it finishes, answers come only from the `college_data/` files. Admins can follow the progress in the **Website sync** panel.

**Check it:**
```bash
docker compose ps                          # all containers "running"; backend "healthy" after start-up
curl https://<your-domain>/api/health      # {"status":"healthy","database":"ok",...,"llm":"ok"}
docker compose logs -f backend             # live logs (Ctrl+C to stop watching)
```

Then open `https://<your-domain>`, sign up with the admin email, and check the Website sync panel.

## Switching to the college DGX LLM

The backend talks to any server with an OpenAI-compatible API. vLLM, Ollama and TGI all provide one. Switching needs no code change:

1. **Start the model on the DGX server**, for example:
   - vLLM: `vllm serve openai/gpt-oss-120b --api-key <a-secret>`, which gives an API on port 8000
   - Ollama: `ollama serve`, which gives an API on port 11434
2. **Make sure the app server can reach it.** On the college network this works directly. Across the internet (from Oracle), expose it only over HTTPS with an API key, or use a VPN. This is one reason to move the app onto a college server in the end.
3. **In `backend/.env`:**
   ```
   LLM_BASE_URL=http://<dgx-host>:8000/v1    # Ollama: http://<dgx-host>:11434/v1
   LLM_MODEL=<model name, as listed at <LLM_BASE_URL>/models>
   LLM_API_KEY=<the secret, or empty>
   LLM_REASONING_EFFORT=                     # keep "low" only for gpt-oss models
   ```
4. **Apply and check:**
   ```bash
   docker compose up -d backend                                   # "restart" doesn't re-read .env
   docker compose exec backend python -m scripts.check_llm        # one test question
   docker compose exec backend python -m scripts.eval_answers --delay 0
   ```
   `eval_answers` asks 22 real questions, including Hindi, Marathi and Hinglish ones. Aim for at least 85% passing before relying on the new model.

## Everyday commands

| Task | Command |
|---|---|
| Status | `docker compose ps` |
| Logs | `docker compose logs -f backend` (or `web`, `db`, `backup`) |
| Install a new version | `git pull && docker compose up -d --build` |
| Apply a `backend/.env` change | `docker compose up -d backend` |
| Restart the backend | `docker compose restart backend` |
| Stop everything | `docker compose down` (data is kept) |

> **Never run `docker compose down -v`:** `-v` deletes the volumes, which means the database and the knowledge base.

**Backups:**
- **Where they are:** `backups/college_ai-YYYY-MM-DD.dump`, one per day, kept 14 days.
- **Copy them off the server regularly**, for example with `scp` to your PC or `rclone` to Google Drive. A backup on the same disk is lost together with the server.
- **To restore one:**
  ```bash
  docker compose stop backend
  docker compose exec -T db pg_restore --clean --if-exists -U college_ai -d college_ai < backups/college_ai-2026-10-01.dump
  docker compose start backend
  ```
- **The knowledge base isn't backed up:** it's rebuilt from the website. To start it fresh: `docker compose down && docker volume rm smart-campus-connect_chroma && docker compose up -d`.

## Notes

- **One backend process only:** don't add uvicorn `--workers` or scale the backend container. The website-sync scheduler, its progress and the login rate limits live in the process's memory.
- **Security checklist:**
  - new `JWT_SECRET` and a strong `POSTGRES_PASSWORD`
  - API docs off (the default here)
  - only ports 22, 80 and 443 open
  - SSH with a key only
  - Ubuntu security updates on (`unattended-upgrades` is installed by default)
- **LLM limit right now:** Groq's free tier allows about 3 questions per minute for the whole app. Beyond that, users see "The assistant is getting a lot of questions right now…". This is fine for a demo; the DGX server removes the limit.
- **Failed website syncs** are emailed to `ADMIN_EMAIL`, at most once a day.
