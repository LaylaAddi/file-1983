# File 1983 — Rebuild Status & Next Phase Handoff

## Where We Are

This is a clean rebuild of the old `1983-law` repo. The new site will live at **file1983.com**.

---

## What Is Built ✓

### Step 1 — Project Scaffold ✓
- Django project named `config` (`config/settings.py`)
- Apps: `accounts`, `documents`, `public_pages`
- Dynamic admin URL: `ADMIN_URL` env var (default `manage-dev/`)
- DRF + JWT wired at `/api/v1/` (stubbed — for mobile app later)
- `base.html` — exact design from old repo (patriot theme, dark mode, animated flag footer)
- `static/css/app-theme.css` + `public-pages.css` — exact originals
- All 4 SVGs — exact originals (gavel-icon, gavel-logo, gavel, favicon)
- Docker + docker-compose + `.env` support

### Step 2 — `accounts` app ✓
- Custom `User` model (email-based, no username)
- `Subscription`, `DocumentPack`, `SiteSettings` (singleton), `LegalDocument` models
- Auth views: login, register, logout, profile, password reset
- All auth templates — styled with patriot theme
- Initial migration done

### Step 3 — Frontend Content ✓
- `public_pages` app: full CMS models (`CivilRightsPage`, `PageSection`), admin with inline sections
- All public pages from old repo: home/landing, know your rights, section 1983, 4th/5th amendments, right to record, rights violated, first amendment auditors
- 13 CMS section partials (accordion, cards, hero, CTA, stats, two-column, checklist, etc.)
- Legal pages: terms, privacy, disclaimer, cookies (served at `/legal/*/`)
- CMS dynamic pages at `/page/<slug>/`
- All `1983law.org` → `file1983.com` and `1983 Law` → `File 1983` references updated
- No ckeditor dependency — plain `TextField` used throughout
- Pricing template exists but **Stripe is NOT wired** (intentionally deferred)

---

## What Is NOT Built Yet

- **Document creation** — the core feature (next focus)
- Stripe / payments — deferred until after documents work
- AI integration (OpenAI) — deferred
- PDF generation (WeasyPrint) — deferred
- Video evidence (Supadata) — deferred
- `public_pages` CMS — models exist, admin works, but no content seeded
- Referral program — deferred
- Sitemap / SEO polish — deferred
- Render deploy config — deferred

---

## Running Locally

```bash
# Pull latest
git fetch origin
git merge origin/claude/review-handoff-AeJJC
git push origin master

# Start
docker-compose up --build -d
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser

# Visit
http://localhost:8000/              # Landing page
http://localhost:8000/manage-dev/   # Admin (or whatever ADMIN_URL is set to)
```

### `.env` minimum
```
SECRET_KEY=dev-secret-key-local
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
ADMIN_URL=your-secret-path/
```

---

## Project Structure

```
file-1983/
├── config/             # Django project (settings, urls, wsgi, context_processors)
├── accounts/           # User, Subscription, DocumentPack, SiteSettings, LegalDocument
├── documents/          # STUB — models/views to be built next
├── public_pages/       # CMS pages, section partials, legal pages
├── static/
│   ├── css/app-theme.css       # Master theme (exact original)
│   └── css/public-pages.css    # Public pages styles (exact original)
├── static/images/      # All 4 SVG logos (exact originals)
├── templates/
│   ├── base.html               # Master layout (exact original design)
│   ├── accounts/               # login, register, profile, pricing, password reset
│   ├── documents/              # STUB — list.html placeholder only
│   ├── legal/                  # terms, privacy, disclaimer, cookies
│   └── public_pages/           # All public pages + 13 section partials
├── manage.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Next Phase — Document Creation

**Goal:** Build the core document creation flow step by step, one piece at a time.
Do not rush ahead. Each sub-step should be reviewed before moving to the next.

### Priority Order

**Sub-step A — `documents` app: Models + Migration**
Define the clean data model. No views yet.
- `Document` — belongs to user, short random slug, `payment_status` (draft/paid/finalized/expired)
- `WizardSession` — tracks wizard progress, `current_step` (1-7), `story_text`, `ai_analysis` (JSON)
- `PlaintiffInfo` — name, address, contact
- `IncidentOverview` — date, time, city, state, county, `federal_district_court`
- `Defendant` — name, title, agency, badge number (multiple per document)
- `IncidentNarrative` — detailed narrative text
- `RightsViolated` — amendments checked (multiple)
- `Witness` — name, contact, description (multiple)
- `Evidence` — type, description, file reference (multiple)
- `Damages` — physical, emotional, financial, other
- `ReliefSought` — what the plaintiff is asking for
- `AIPrompt` — admin-managed prompts for each AI task
- Run migration, register everything in admin

**Sub-step B — Document List + Create Views**
- `/documents/` — list of user's documents (requires login)
- `/documents/new/` — create a new document (stub, no wizard yet)
- `/documents/<slug>/` — document detail / hub page
- Simple templates, no wizard yet

**Sub-step C — The Wizard (7 steps)**
This is the main UX. Alpine.js, one step at a time.
Step 1: Story input (free text)
Step 2: Plaintiff Info
Step 3: Incident Overview (date, location)
Step 4: Defendants
Step 5: Rights Violated
Step 6: Evidence & Witnesses
Step 7: Damages & Relief
- AJAX saves per step
- No AI yet — just save the form data

**Sub-step D — AI Integration**
- `openai_service.py` — story parsing, section generation
- `AIPrompt` model used for admin-editable prompts
- Trigger from wizard: "Analyze My Case" button

**Sub-step E — Court Lookup**
- Static city→court lookup + GPT fallback
- Wired into wizard Step 3

**Sub-step F — Final Review + PDF**
- Final review page
- WeasyPrint PDF generation

**Sub-step G — Payments (Stripe)**
- Stripe checkout after document is complete
- Webhooks
- Gate PDF download behind payment

---

## Key Technical Decisions Already Made

| Decision | Value |
|----------|-------|
| Auth model | `accounts.User` (email-based) |
| Document URL ID | Short random slug via `secrets.token_urlsafe(6)` — never expose PK |
| Dark mode | `data-theme="dark"` on `<html>` (NOT Bootstrap's `data-bs-theme`) |
| Theme toggle key | `localStorage` key: `file1983_theme` |
| Admin URL | `ADMIN_URL` env var |
| API auth | JWT (`djangorestframework-simplejwt`) |
| Static files | WhiteNoise |

---

## Important Notes for Next Session

1. **Start with Sub-step A** — define all models first, get them right, then build views
2. **One sub-step at a time** — do not jump ahead
3. **No Stripe yet** — the pricing page exists but checkout is not wired
4. **No AI yet** — wizard saves plain form data first, AI comes in Sub-step D
5. **Slugs are immutable** — generate on `Document.save()` only if blank, never regenerate
6. **Login required** on all document views
7. **Ownership check** on every document view — users can only access their own docs
