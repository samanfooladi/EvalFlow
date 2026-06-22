# EvalFlow — Architecture

This document describes how EvalFlow is actually built: the system's
purpose, its high-level shape, the backend/frontend module layout, the data
model, the request/permission flow, the document-generation pipeline, and
the security posture. For roadmap items not yet built, see `BACKLOG.md`.

## 1. What the system does

EvalFlow runs the documentation half of a security-evaluation lab's
workflow. A lab assesses vendor products/systems against one of two
requirement frameworks:

- **TRP** — a functional security test, structured as Common-Criteria-style
  SFR classes → components → individual testable sub-clauses.
- **VTR** — a vulnerability test, structured as OWASP Testing Guide (OTG)
  categories → numbered test cases.

For each **assessment** (one system × one framework), the system fans out a
row per clause/sub-clause, lets the assigned **assessor** mark each
sub-clause compliant / finding / not-applicable and write up the test
narrative (with auto-generated default text and inline evidence images),
routes the assessment through **assessor → reviewer → completed**, and
generates the lab's official Persian, right-to-left Word documents:

- **TRP/VTR** — the full report.
- **BRP** — a findings-only extract, generated from the same data.

Everything is built for a hostile-user threat model (the users are
penetration testers): strict role-scoped querysets, no client-trusted
authorization, append-only audit logging, and upload validation by content,
not extension.

## 2. High-level shape

```
┌─────────────────────┐        HTTPS, same-origin           ┌──────────────────────────┐
│  React 18 + TS SPA   │ ───────────────────────────────────▶│  Django 5.2 + DRF API    │
│  (Vite, Tailwind v4) │  Bearer access token (in memory)     │  /api/v1/...             │
│  RTL, Persian-only   │◀───────────────────────────────────  │  JWT rotation + blacklist│
└─────────────────────┘        httpOnly refresh cookie        └────────────┬─────────────┘
                                  (path-scoped to /auth)                    │
                                                                            ▼
                                                              ┌──────────────────────────┐
                                                              │  MySQL 8.4 (SQLite dev)  │
                                                              └──────────────────────────┘
                                                                            │
                                                              ┌─────────────┴────────────┐
                                                              │  apps/reports/services   │
                                                              │  python-docx generators  │
                                                              │  → streamed .docx file   │
                                                              └──────────────────────────┘
```

In dev, Vite proxies `/api` to the Django dev server so the frontend and
backend share an origin (cookies stay first-party; no CORS needed in prod).
In prod, nginx serves the built SPA and reverse-proxies `/api` to gunicorn —
see `deploy/nginx.conf.example` and `docker-compose.yml`.

## 3. Backend — Django apps

The backend is split into single-responsibility Django apps under
`backend/apps/`, each owning its own models/serializers/views/urls:

```
backend/
├── evalflow/
│   ├── settings/{base,dev,prod,test}.py   # env-driven; prod hardens what dev relaxes
│   ├── urls.py                            # mounts each app under /api/v1/
│   └── wsgi.py
├── apps/
│   ├── accounts/      # custom User, roles, JWT auth views, RolePermission/
│   │                   IsAssignedOrElevated (the single RBAC source)
│   ├── catalog/        # Company, ProductSystem — who/what is being assessed
│   ├── frameworks/     # Framework, Requirement, Clause, SubClause,
│   │                   DefaultTextTemplate — the assessable content,
│   │                   loaded from fixtures, never user-generated
│   ├── assessments/    # Assessment, ClauseAssessment, SubClauseAssessment,
│   │                   Attachment — the live per-assessment work, status
│   │                   transitions, evidence/image uploads
│   ├── audit/          # append-only AuditLog + middleware that captures
│   │                   request context (ip, user-agent) for every mutation
│   └── reports/        # no models — services/ only: docx_utils.py (low-
│                       level oxml/RTL helpers) + trp/vtr/brp_generator.py
└── tests/              # pytest-django + factory-boy; one file per concern
    (test_auth, test_rbac, test_models, test_transitions, test_uploads,
     test_clause_images, test_docx, test_api)
```

**Why this split:** `frameworks` (what *can* be tested) is strictly
separate from `assessments` (what *was* tested, by whom, with what
verdict) — the same framework drives many assessments, and framework
content is lab-curated reference data, not user input. `reports` has no
models at all; it's a pure transform from `assessments` state to a
`BytesIO` docx, which keeps the highest-risk code (binary file generation)
isolated and easy to test with XML assertions.

## 4. Data model

```
User (accounts) ─────────────────┐
  role: admin|assessor|reviewer|qa_lead
                                  │
Company ──< ProductSystem        │ assessor / reviewer / created_by / uploaded_by
   (catalog)                     │
        │                        │
        └──< Assessment >────────┘
               │  system, framework, status, tester/approver codes,
               │  architecture_overview, test_configuration, change_log
               │
               ├──< ClauseAssessment >── Clause (frameworks, read-only)
               │       │   status (derived), text, text_edited
               │       │
               │       ├──< SubClauseAssessment >── SubClause (frameworks)
               │       │       status, notes
               │       │       └──< Attachment (evidence, scoped to sub-clause)
               │       │
               │       └──< Attachment (clause-text image library,
               │               scoped to clause_assessment + uploaded_by,
               │               referenced via [[filename_slug]] tokens)
               │
               └──< Attachment (assessment-level, no clause)

Framework ──< Requirement ──< Clause ──< SubClause     (frameworks, lab-curated)
Framework ──< DefaultTextTemplate (per status, {{placeholder}} substitution)

AuditLog: actor (User), action, model, object_id, object_repr, changes JSON,
          ip, user_agent — append-only (save()/delete() raise after creation)
```

Key points:
- `Assessment.create_clause_assessments()` fans out one `ClauseAssessment`
  per `Clause` and one `SubClauseAssessment` per `SubClause`, idempotently,
  when an assessment is created.
- A clause's **status is derived** from its sub-clauses (e.g. any finding ⇒
  clause is a finding), never set directly by the client.
- `ClauseAssessment.text` gets the framework's `DefaultTextTemplate`
  rendered for the current status, unless the assessor has already
  hand-edited it (`text_edited=True`), in which case status changes never
  clobber their words.
- `Attachment` plays two roles distinguished by FK: evidence (linked to a
  `SubClauseAssessment`) and clause-text images (linked to a
  `ClauseAssessment` + `uploaded_by`, unique per
  `(clause_assessment, uploaded_by, filename_slug)`), feeding the
  `[[filename_slug]]` inline-image placeholder system used in exports.

## 5. API & permission model

Single router prefix `/api/v1/`, mounted per-app in `evalflow/urls.py`.
Authorization is centralized in `apps/accounts/permissions.py`:

- **`RolePermission`** — each `ViewSet` declares `allowed_roles: dict[action, frozenset[Role]]`; this is the one place that says who may call which action. No view re-implements role checks ad hoc.
- **`IsAssignedOrElevated`** — object-level check: admins/QA leads (`user.is_elevated`) pass for any object; everyone else must be the assessment's `assessor` or `reviewer`. Querysets are *also* pre-filtered by role in `get_queryset()`, so unassigned users get a 404 (object doesn't exist for them), not a 403 (which would leak existence) — the standard IDOR defense used throughout.
- **Status-gated mutation** — clause/sub-clause edits and image uploads only succeed while `Assessment.status == under_assessment` (`_check_editable`); workflow transitions go through `apps/assessments/transitions.py`, an explicit allowed-edges table per role, never a raw status PATCH.

Endpoint groups:

| Area | Examples |
|---|---|
| Auth | `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me`, `POST /auth/change-password` |
| Catalog | `/companies/`, `/systems/` |
| Frameworks (read-mostly) | `/frameworks/`, `/requirements/`, `/clauses/` |
| Assessments | `/assessments/`, `/assessments/{id}/transition/`, `/assessments/{id}/clause-assessments/`, `/assessments/{id}/export/?type=trp\|vtr\|brp` |
| Clause work | `/clause-assessments/{id}/` (PATCH text), `/reset-text/`, `/images/` (GET/POST), `/sub-clause-assessments/{id}/` |
| Attachments | `/assessments/{id}/attachments/`, `/attachments/{id}/download/`, `/attachments/{id}/inline/` |
| Audit | `/audit-logs/` (read-only) |

## 6. Document generation (`apps/reports/services/`)

```
docx_utils.py   low-level oxml helpers: set_paragraph_rtl (w:bidi),
                set_run_fonts (Times New Roman + B Nazanin cs font, w:rtl),
                shade_cell (w:shd F2F2F2), set_table_rtl (w:bidiVisual),
                page setup, header/footer, Shamsi dates via jdatetime
common.py       shared per-clause table builder, evidence-image embedding,
                [[token]] placeholder resolution (IMAGE_TOKEN_RE)
trp_generator.py / vtr_generator.py / brp_generator.py
                cover → change log → metadata/profile → free text →
                per-clause result tables; BRP filters to findings only
```

Documents are built **programmatically with python-docx**, not from a
template file — table row counts are data-driven (N clauses), and
template-replacement tooling can't clone RTL-formatted tables cleanly.
`[[filename_slug]]` tokens inside `ClauseAssessment.text` are resolved at
export time against that exact `(clause_assessment, filename_slug)`
attachment; unresolvable tokens render a visible
`[تصویر یافت نشد: token]` warning instead of raising. The endpoint blocks
export while any clause is unreviewed (admins/QA leads can override with
`?allow_incomplete=1`), streams the result as a `FileResponse`, and writes
an `export_docx` audit row.

## 7. Frontend

```
frontend/src/
├── api/            axios client (silent refresh on 401) + types.ts mirrors
├── auth/            AuthProvider (token in memory, refresh via cookie),
│                    RequireAuth / RequireRole route guards
├── components/      AppShell (nav/layout) + small design-system primitives
│                    (Button, Textarea, Badge, ErrorText, …) in ui.tsx
├── features/
│   ├── companies/   company + system CRUD
│   ├── assessments/
│   │   ├── AssessmentsPage.tsx        list/create
│   │   └── workspace/                 the main assessment workspace:
│   │       ClauseSidebar (grouped by class + status filters),
│   │       ClauseEditor (status radios, text + image-placeholder editor
│   │         with live preview, evidence attachments),
│   │       AttachmentsPanel, WorkspacePage (layout), useWorkspace.ts
│   │         (all TanStack Query hooks for this feature)
│   ├── frameworks/  admin framework/clause editor
│   ├── users/        admin user management
│   └── audit/        audit log viewer
└── pages/LoginPage.tsx
```

Routing (`App.tsx`) is flat: `RequireAuth` wraps everything but `/login`;
`RequireRole` gates `/admin/*` routes by role. Server state is owned by
TanStack Query (`useWorkspace.ts` hooks) — no separate client-side store;
the server is the single source of truth and the UI invalidates/refetches
on mutation rather than hand-rolling optimistic caches except where it's
cheap (e.g. patching one clause in the list cache).

## 8. Security architecture

- **Auth**: SimpleJWT — short-lived access token kept in memory (never
  localStorage), rotating refresh token in an httpOnly, `Secure`,
  `SameSite=Strict` cookie scoped to `/api/v1/auth`, with blacklist-on-
  rotation so a stolen refresh token can't be replayed after use.
- **Passwords**: Argon2 as the first hasher, Django's standard validators.
- **Throttling**: login attempts rate-limited per IP; failures produce
  `login_fail` audit rows.
- **Transport/headers** (prod): forced HTTPS + HSTS (1y, preload,
  subdomains), `X-Content-Type-Options: nosniff`, same-origin referrer
  policy, secure cookies.
- **Uploads**: extension allow-list **and** `python-magic` content
  sniffing (rejects renamed/double-extension files), size cap, UUID
  filenames under `MEDIA_ROOT` — never served by path, only through
  authenticated endpoints (`download/`, `inline/`) that set
  `Content-Disposition` and `nosniff` explicitly.
- **IDOR defense**: every list/detail queryset is pre-filtered by the
  requesting user's role/assignment before any object-level permission
  check runs; unassigned users get 404s, not 403s.
- **Audit**: append-only `AuditLog` (model-level `save()`/`delete()` raise
  after the first write) populated via a request-context middleware plus
  explicit `log_event()` calls on every mutating action, including
  exports and uploads.
- **Templating**: `DefaultTextTemplate` uses plain `str.replace` on a
  fixed placeholder whitelist — never a real template engine — to keep
  SSTI off the table even though the templates are admin-authored.

## 9. Deployment

- **Dev**: SQLite + Django dev server + Vite dev server (proxying `/api`),
  no Docker required (`README.md` quick start).
- **Prod**: `docker-compose.yml` runs MySQL 8.4 + gunicorn (Django,
  `evalflow.settings.prod`); the frontend is built statically
  (`vite build`) and served by nginx alongside a reverse proxy to the
  backend (`deploy/nginx.conf.example`). No CORS is needed in prod since
  everything is same-origin behind nginx.
