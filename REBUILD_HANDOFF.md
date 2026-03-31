# File 1983 — Session Handoff

## Picking Up This Project

Read this entire document before writing a single line of code.
Work on branch `claude/review-handoff-AeJJC`. Push there. Never push to master directly.

---

## The App

A Django web app at **file1983.com** that guides users through building a
**Section 1983 civil rights complaint** against government officials.
Users describe their incident, fill out a 7-step wizard, and receive a
complete legal document (PDF).

---

## Stack

- **Backend:** Django 4.2, PostgreSQL (prod), SQLite (dev)
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, Playfair Display, Alpine.js
- **Theme:** American flag color palette, dark mode via `data-theme="dark"` on `<html>`
- **Auth:** Custom email-based User model (`accounts.User`)
- **AI:** OpenAI (deferred — not yet)
- **Payments:** Stripe (deferred — not yet)
- **PDF:** WeasyPrint (deferred — not yet)
- **Hosting:** Render (not yet deployed)

---

## What Is Already Built

### accounts app ✓
- `User` — email-based, no username, has `referral_code`, `referred_by`
- `Subscription` — Stripe subscription tracking (monthly/annual)
- `DocumentPack` — one-time purchase credits
- `SiteSettings` — singleton (app_name, header_app_name, pricing, feature flags)
- `LegalDocument` — terms/privacy/disclaimer content
- Views: login, register, logout, profile, password reset
- Migration: `accounts/migrations/0001_initial.py`

### public_pages app ✓
- `CivilRightsPage` + `PageSection` CMS models
- All public pages: home, know your rights, section 1983, amendments, right to record, etc.
- Legal pages: terms, privacy, disclaimer, cookies at `/legal/*/`
- Dynamic CMS pages at `/page/<slug>/`
- Migration: `public_pages/migrations/0001_initial.py`

### documents app — STUB ONLY
- `documents/views.py` — placeholder list/create views only
- `documents/urls.py` — only has `list` and `create` stub routes
- `documents/models.py` — empty
- **No migration exists yet for documents**

### Frontend / Design ✓
- `templates/base.html` — exact original design, navbar, footer, dark mode toggle
- `static/css/app-theme.css` — full patriot theme (2764 lines, exact original)
- `static/css/public-pages.css` — public pages styles (exact original)
- `static/images/` — all 4 SVGs (exact originals from old repo)
- All templates use `data-theme="dark"` for dark mode (NOT Bootstrap's `data-bs-theme`)

### Infrastructure ✓
- `config/settings.py` — all env vars wired, `AUTH_USER_MODEL = 'accounts.User'`
- `config/urls.py` — ADMIN_URL dynamic, all apps routed
- `config/context_processors.py` — injects `app_name`, `header_app_name`, `ADMIN_URL`
- `Dockerfile` + `docker-compose.yml` — working locally
- `requirements.txt` — all deps listed

---

## Running Locally

```bash
docker-compose up --build -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

`.env` minimum:
```
SECRET_KEY=any-dev-secret
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
ADMIN_URL=your-secret-path/
```

---

## URL Structure (current)

```
/                           public_pages:home
/rights/                    public_pages:know_your_rights
/rights/section-1983/       public_pages:section_1983
/rights/record-police/      public_pages:right_to_record
/rights/fourth-amendment/   public_pages:fourth_amendment
/rights/fifth-amendment/    public_pages:fifth_amendment
/rights/violated/           public_pages:rights_violated
/rights/first-amendment-auditors/  public_pages:first_amendment_auditors
/page/<slug>/               public_pages:cms_page
/legal/terms/               public_pages:terms
/legal/privacy/             public_pages:privacy
/legal/disclaimer/          public_pages:disclaimer
/legal/cookies/             public_pages:cookies
/accounts/login/            accounts:login
/accounts/register/         accounts:register
/accounts/logout/           accounts:logout
/accounts/profile/          accounts:profile
/accounts/password-reset/   accounts:password_reset
/documents/                 documents:list  (stub)
/documents/new/             documents:create (stub)
/<ADMIN_URL>/               Django admin
/api/v1/token/              JWT token
/api/v1/token/refresh/      JWT refresh
```

---

## What To Build Next — Document Creation

The user will describe the exact fields they want before you write any models.
**Wait for that description before writing code.**

The intended build order is strictly:

### Sub-step A — Models + Migration
Wait for the user to describe their desired fields, then build all `documents` models cleanly.
Key models needed (details TBD by user):
- `Document` — the top-level record, belongs to user, short random slug
- `WizardSession` — tracks progress through the 7-step wizard
- Per-step data models (plaintiff, incident, defendants, rights, evidence, damages, relief)
- `AIPrompt` — admin-managed prompts

Slug rule: generate on `Document.save()` using `secrets.token_urlsafe(6)` only if blank.
Never regenerate. Never expose database PK in URLs.

### Sub-step B — Document List + Create + Detail Views
After models are confirmed and migrated:
- `/documents/` — list user's documents
- `/documents/new/` — create new document
- `/documents/<slug>/` — document hub/detail page
- All views require login
- All views check document ownership

### Sub-step C — The 7-Step Wizard
- Alpine.js single-page interface at `/documents/<slug>/wizard/`
- One step at a time — no AI yet, just save form data
- AJAX saves per step

### Sub-step D — AI Integration (deferred)
### Sub-step E — Court Lookup (deferred)
### Sub-step F — PDF Generation (deferred)
### Sub-step G — Stripe Payments (deferred)

---

## Key Rules For This Project

1. **One sub-step at a time.** Do not jump ahead.
2. **Ask before building models.** The user will define the exact fields.
3. **No Stripe yet.** The pricing template exists but checkout is not wired.
4. **No AI yet.** Wizard saves plain form data first.
5. **Slugs are immutable.** Generate once, never overwrite.
6. **Login required** on all document views.
7. **Ownership check** on every document view.
8. **Branch:** always work on `claude/review-handoff-AeJJC`
9. **Push format:** `git push -u origin claude/review-handoff-AeJJC`
10. **Dark mode:** uses `data-theme="dark"` on `<html>`, not `data-bs-theme`

---

## Important File Locations

| File | Purpose |
|------|---------|
| `config/settings.py` | All settings + env vars |
| `config/urls.py` | Root URL config |
| `config/context_processors.py` | Injects app_name, ADMIN_URL into templates |
| `accounts/models.py` | User + auth models |
| `documents/models.py` | EMPTY — build here next |
| `documents/views.py` | Stub only — replace in Sub-step B |
| `documents/urls.py` | Stub only — replace in Sub-step B |
| `templates/base.html` | Master layout — do not redesign |
| `static/css/app-theme.css` | Master CSS — do not replace |

---

## Git Commands (for every session)

```bash
# Start of session — get latest
git fetch origin
git checkout claude/review-handoff-AeJJC
git pull origin claude/review-handoff-AeJJC

# Push work
git push -u origin claude/review-handoff-AeJJC

# User merges to master locally
git fetch origin
git merge origin/claude/review-handoff-AeJJC
git push origin master
```
