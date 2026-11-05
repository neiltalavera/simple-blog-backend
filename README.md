# FastAPI Blog API

A small blog backend with user accounts, posts, comments, and one reaction per user per post. FastAPI serves the API, SQLAlchemy talks to PostgreSQL, and Alembic manages schema changes.

## Run locally

1. Create and activate a virtual environment, then install dependencies:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Start PostgreSQL and configure the app:

   ```powershell
   docker compose up -d db
   Copy-Item .env.example .env
   ```

   Set `JWT_SECRET_KEY` in `.env` to a long random value before running the API.

3. Create the tables and start the server:

   ```powershell
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

Open `http://127.0.0.1:8000/docs` to explore the API.

## Main endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Create an account |
| POST | `/api/v1/auth/login` | Get a JWT access token |
| GET | `/api/v1/auth/me` | View the signed-in user |
| GET / POST | `/api/v1/posts` | List or publish posts |
| GET / PATCH / DELETE | `/api/v1/posts/{post_id}` | View or manage a post (author only for changes) |
| GET / POST | `/api/v1/posts/{post_id}/comments` | List or add comments |
| PUT / DELETE | `/api/v1/posts/{post_id}/reaction` | Add or remove your reaction |

For protected endpoints, send `Authorization: Bearer <token>`. Add `?limit=20&offset=0` to list endpoints to paginate.

## Safety basics

Passwords use Argon2 hashing, JWTs expire, request bodies are validated, database queries use SQLAlchemy parameters, and write access is checked against the post owner. CORS, request rate limits, and basic security headers are configured. Keep secrets in environment variables and use HTTPS in production.
