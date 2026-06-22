# EvalFlow

Streamlined workflow and documentation management for security assessments. From review to final report, without the paperwork overhead.

EvalFlow manages the lifecycle of TRP (functional security test) and VTR
(vulnerability test) assessments: companies and systems are registered,
assessors review each requirement clause (compliant / finding /
not-applicable) with auto-generated editable text, reviewers approve, and
the system produces the official **Persian RTL Word documents** — the full
TRP/VTR report plus a BRP package containing only the findings.

## Stack

- **Backend**: Django 5.2 + Django REST Framework, MySQL (SQLite fallback for dev)
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS v4, Persian RTL, dark UI
- **Auth**: JWT — 15-minute access token in memory, rotating refresh token in an httpOnly cookie, server-side blacklist
- **Documents**: python-docx with native RTL (bidi) support, B Nazanin typography, Shamsi dates

## Quick start (development)

```bash
# Backend (SQLite by default; set DB_ENGINE=mysql to use MySQL)
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py load_frameworks   # TRP + VTR requirement fixtures
.venv/bin/python manage.py seed_demo         # demo users (prints password)
.venv/bin/python manage.py runserver

# Frontend (separate terminal; proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and log in with the seeded `admin` /
`assessor` / `reviewer` / `qalead` users.

## Tests

```bash
cd backend && .venv/bin/python -m pytest
```

The suite covers auth flows (rotation, replay, throttling), the full
endpoint × role RBAC matrix, IDOR attempts, upload abuse (magic-byte
mismatches, double extensions, oversize), workflow transitions, default-
text templating, and XML-level assertions on the generated Word documents.

## Production

```bash
cp .env.example .env   # set DJANGO_SECRET_KEY, DB_PASSWORD, hosts
docker compose up -d   # MySQL 8.4 + gunicorn backend
npm --prefix frontend run build
# serve frontend/dist + proxy /api via nginx — see deploy/nginx.conf.example
```

Production uses `evalflow.settings.prod`: HSTS, SSL redirect, strict
security headers, Argon2 password hashing, login throttling, append-only
audit log, and role-scoped querysets throughout.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design: data model,
API/permission model, document-generation pipeline, and security posture.

## Project layout

```
backend/   Django project (apps: accounts, catalog, frameworks,
           assessments, audit, reports)
frontend/  React SPA (RTL, Persian-only UI)
deploy/    nginx example configuration
BACKLOG.md Bucket 2 / Bucket 3 scope — nothing enters the release directly
```
