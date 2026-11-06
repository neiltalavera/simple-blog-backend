# Morrowlog
Visit website: https://morrowlog.snlc.workers.dev/

# FastAPI Blog API

A small blog backend with user accounts, posts, comments, and one reaction per user per post. FastAPI serves the API, SQLAlchemy talks to PostgreSQL, and Alembic manages schema changes.

frontend service: [simple-blog-frontend](https://github.com/neiltalavera/simple-blog-frontend)

## Run locally

1. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Configure the app:

   ```powershell
   docker compose up -d db
   Copy-Item .env.example .env
   ```

   For Neon, set `DATABASE_URL` to the **direct** connection string and
   `DATABASE_URL_POOLED` to the **pooled** connection string from the Neon
   dashboard. Both should include `sslmode=require`. The API uses the pooled
   URL; Alembic uses the direct URL when it creates or upgrades tables. For a
   local Docker database, leave `DATABASE_URL_POOLED` empty. Set
   `JWT_SECRET_KEY` in `.env` to a long random value before running the API.

3. Create the tables and start the server:

   ```powershell
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

Open `http://127.0.0.1:8000/docs` to explore the API.

## Main endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/access-request` | Request an invite code |
| POST | `/api/v1/auth/register` | Create an account with an email-matched invite code |
| POST | `/api/v1/auth/login` | Get a JWT access token |
| GET | `/api/v1/auth/me` | View the signed-in user |
| GET / POST | `/api/v1/posts` | List or publish posts |
| GET / PATCH / DELETE | `/api/v1/posts/{post_id}` | View or manage a post (author only for changes) |
| GET / POST | `/api/v1/posts/{post_id}/comments` | List or add comments |
| PUT / DELETE | `/api/v1/posts/{post_id}/reaction` | Add or remove your reaction |

For protected endpoints, send `Authorization: Bearer <token>`. Add `?limit=20&offset=0` to list endpoints to paginate.

## Access requests and Discord notifications

Registration starts with an access request or an invite code. Access requests accept a valid email once and post the email plus a generated code to Discord; send the code to the requester manually within 1–3 business days. The code is bound to that email. Five incorrect code attempts permanently lock the email from registering or requesting another code. Requests are limited to five per hour per IP.

Set `DISCORD_WEBHOOK_URL` and `DISCORD_UID` in the backend `.env` file. Access requests post an embed titled `New Access Request`; successful logins post an embed titled `User Login`. Both use color `5814783` and mention the configured Discord user. The webhook URL and Discord UID stay on the backend and are never returned to the frontend. The mention allowlist is restricted to that configured user.

Discord delivery runs after the API response and does not block or fail the request. If Discord responds with HTTP 429, the backend waits for its `Retry-After` value and retries once. Delivery failures are logged without logging the webhook URL.

Run the focused notification tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Safety basics

Passwords use Argon2 hashing, JWTs expire, request bodies are validated, database queries use SQLAlchemy parameters, and write access is checked against the post owner. CORS, request rate limits, and basic security headers are configured. Keep secrets in environment variables and use HTTPS in production.
