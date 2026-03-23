# 1983 Law — Clean Rebuild Handoff

## What This Is
A step-by-step rebuild of 1983law.org from scratch. Same stack, clean database, cleaner code.
Build everything from this spec. Nothing is copied from an old codebase.

---

## The App
A Django web app at **file1983.com** that guides users through building a **Section 1983 civil rights complaint**
against government officials. Users tell their story, the AI analyzes it, and the wizard walks
them through 7 steps to produce a complete legal document (PDF).

---

## Stack
- **Backend:** Django 4.2+, PostgreSQL (prod), SQLite (dev)
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, Playfair Display (Google Font), Alpine.js (wizard)
- **AI:** OpenAI API (GPT-4) — story parsing, section generation, court lookup fallback
- **Payments:** Stripe — one-time purchases + subscriptions + webhooks
- **PDF:** WeasyPrint
- **Video Evidence:** Supadata API (YouTube transcript extraction)
- **Hosting:** Render (gunicorn + whitenoise)
- **Auth:** Custom user model, email-based (no username)

---

## Design — Keep As-Is
The front end design and logo carry over from the old app. Do not redesign.

### Color Palette (American flag theme)
```css
--patriot-blue: #002868
--patriot-blue-light: #003d99
--patriot-blue-dark: #001a4d
--patriot-red: #BF0A30
--patriot-red-light: #d4213f
--patriot-white: #FFFFFF
--patriot-cream: #F8F9FA
--patriot-gold: #B8860B
```

### Logo / Icons
Stored in `static/` in the old repo:
- `gavel-icon.svg` — navbar icon (24x24 in a rounded box)
- `gavel-logo.svg` — full logo
- `gavel.svg` — standalone gavel
- `favicon.svg` — browser tab icon

### Fonts
- **Headings:** Playfair Display (600, 700) — loaded from Google Fonts
- **Body:** system-ui stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto...`)

### Navbar
Dark patriot-blue gradient, gavel icon + app name as brand. Copy `navbar-patriot` styles
from `static/css/app-theme.css` in the old repo.

### Theme CSS
`static/css/app-theme.css` in the old repo is the master theme file — copy it directly.

---

## Django Apps to Build (in this order)

### 1. Project Setup
- Django project named `config` (settings in `config/settings.py`)
- Apps: `accounts`, `documents`, `public_pages`
- Dynamic admin URL: `ADMIN_URL = os.getenv('ADMIN_URL', 'manage-dev/')` in `config/urls.py`
  - Set `ADMIN_URL` as env var on Render with a secret path
- Context processor: `config/context_processors.py` — injects `app_name`, `header_app_name`,
  `user` into all templates (pulled from `SiteSettings` model)
- `base.html` template with navbar, footer, dark mode toggle, Bootstrap 5.3 + Bootstrap Icons

### 2. `accounts` app
Models:
- `User` — custom, email-based (no username field), `AUTH_USER_MODEL = 'accounts.User'`
- `Subscription` — tracks Stripe subscription (monthly/annual), status, period dates
- `DocumentPack` — one-time purchase credits (e.g. 3-pack)
- `SiteSettings` — singleton: `app_name`, `header_app_name`, pricing values, feature flags
- `LegalDocument` — terms/privacy/disclaimer pages managed via admin (CKEditor)

Key user methods needed:
- `has_active_subscription` → bool
- `has_unlimited_access` → bool (staff/admin override)
- `get_ai_uses_remaining` → int
- `can_create_document` → bool

Views: login, register, logout, profile, password reset, pricing page, subscription management

Stripe integration:
- Checkout session creation (one-time + subscription)
- Webhook handler at `/accounts/subscription/webhook/`
- Plans: Single doc $49, 3-pack $99, Monthly sub $29, Annual sub $249

### 3. `documents` app
This is the core of the app. Build in this sub-order:

**3a. Models (clean schema)**
- `Document` — belongs to user, has `slug`, `payment_status` (draft/paid/finalized/expired),
  `created_at`, `updated_at`, `title`
- `WizardSession` — tracks wizard progress: `status` (not_started/in_progress/analyzed/completed),
  `current_step` (1-7), `story_text`, `ai_analysis` (JSON)
- `PlaintiffInfo` — name, address, contact
- `IncidentOverview` — date, time, city, state, county, federal_district_court (confirmed bool)
- `Defendant` — name, title, agency, badge_number (multiple per document)
- `IncidentNarrative` — detailed narrative text
- `RightsViolated` — amendments/rights checked (multiple)
- `Witness` — name, contact, description (multiple)
- `Evidence` — type, description, file reference (multiple)
- `Damages` — physical, emotional, financial, other
- `PriorComplaints` — prior complaints filed, outcomes
- `ReliefSought` — what the plaintiff is asking for
- `AIPrompt` — admin-managed prompts for each AI generation task
- `PromoCode` / `PromoCodeUsage` — referral/discount system
- `PayoutRequest` — referral payout tracking

**3b. The Wizard (7 steps)**
The wizard is the entire UX. It's a single-page Alpine.js interface at `/documents/<slug>/wizard/`.

Steps:
1. Your Story (free-text, AI parses into fields)
2. Plaintiff Information
3. Incident Overview (date, location → triggers court lookup)
4. Defendants
5. Rights Violated
6. Evidence & Witnesses
7. Damages & Relief

Flow: Story → Steps 1-7 → "Analyze My Case" (AI) → Review → "Build Complaint" → Final Review → PDF

**3c. Services**
- `openai_service.py` — all AI calls (story parsing, section generation, court lookup fallback)
- `court_lookup_service.py` — static lookup by city/state → GPT fallback
  - Copy `documents/services/court_data/` directory from old repo directly (50 state files, clean data)
- `pdf_service.py` — WeasyPrint document generation
- `youtube_service.py` — Supadata API for video transcript extraction

**3d. URLs**
- `/documents/` — list
- `/documents/new/` — create
- `/documents/<slug>/` — detail/hub page
- `/documents/<slug>/wizard/` — the wizard
- `/documents/<slug>/final/` — final review + edit
- `/documents/<slug>/final/download-pdf/` — generate and download
- `/documents/<slug>/video-analysis/` — video evidence (subscribers only)
- AJAX endpoints for wizard saves, AI calls, court lookup, PDF status polling

### 4. `public_pages` app
- CMS for landing page and info pages
- Models: `CivilRightsPage`, `PageSection`
- Section types: hero, cards, quotes, CTAs, accordions
- SEO fields per page, publishing controls
- URL: `/` (home), `/page/<slug>/`

---

## Federal Court Lookup
Two-tier system — copy logic from old repo:
1. **Static lookup** — `court_lookup_service.py` dynamically imports state module from
   `documents/services/court_data/states/` and calls `lookup_court_by_city(city)`
2. **GPT fallback** — if city not in static data, calls `openai_service.lookup_federal_court(city, state)`
3. Recreate or stub `court_data/` — static city→court mappings per state; GPT fallback covers any gaps

---

## Slugs
Every `Document` uses a **short random slug** (e.g. `nP27cOkr`) as its URL identifier — never expose
the database integer PK in URLs.

- Generate on save using `secrets.token_urlsafe(6)` or similar, check for collisions
- All document URLs use `<str:document_slug>/` — not `<int:pk>/`
- `CivilRightsPage` (public_pages) also uses a human-readable slug from the title
- Slugs are immutable once set — do not regenerate on update

---

## Mobile API (Build Later — Wire Now)
The web app comes first. Mobile app comes after. But the API layer needs to be set up
from the start so it doesn't require structural changes later.

**Add to project from Step 1:**
- Install `djangorestframework` and `djangorestframework-simplejwt`
- Add to `INSTALLED_APPS`: `rest_framework`, `rest_framework_simplejwt`
- Create `/api/v1/` URL namespace in `config/urls.py` (can be empty to start)
- JWT settings in `settings.py`:
  ```python
  REST_FRAMEWORK = {
      'DEFAULT_AUTHENTICATION_CLASSES': (
          'rest_framework_simplejwt.authentication.JWTAuthentication',
      ),
  }
  ```
- Add token endpoints: `/api/v1/token/`, `/api/v1/token/refresh/`

**API endpoints to build alongside each web feature** (stub them, implement fully later):
- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/login/` (returns JWT)
- `GET/POST /api/v1/documents/` — list + create
- `GET /api/v1/documents/<slug>/` — detail
- `POST /api/v1/documents/<slug>/wizard/save/` — save wizard step
- `POST /api/v1/documents/<slug>/wizard/analyze/` — trigger AI analysis

Mobile will be a React Native or similar app consuming these endpoints.
All API views use JWT auth. All web views use session auth. They share the same models.

---

## Security
- Dynamic admin URL via `ADMIN_URL` env var (never hardcode in repo)
- CSRF on all forms
- Login required on all document views
- Document ownership checks on every view (user can only access their own docs)
- Stripe webhook signature verification

---

## Environment Variables (Render)
```
SECRET_KEY=
DEBUG=0
ALLOWED_HOSTS=file1983.com,www.file1983.com
DATABASE_URL=
ADMIN_URL=your-secret-path/
OPENAI_API_KEY=
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_SINGLE=
STRIPE_PRICE_3PACK=
STRIPE_PRICE_MONTHLY=
STRIPE_PRICE_ANNUAL=
EMAIL_HOST=
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=
SUPADATA_API_KEY=
```

---

## Build Order (Step by Step)
Work through these one at a time. Do not jump ahead.

- [ ] Step 1 — Project scaffold (Django project, apps, settings, base template, theme CSS, logo, DRF + JWT wired up, `/api/v1/` namespace)
- [ ] Step 2 — `accounts` app: User model, auth views, login/register templates
- [ ] Step 3 — `accounts` app: SiteSettings, pricing page, Stripe checkout + webhooks
- [ ] Step 4 — `documents` app: All models, migrations, admin registration
- [ ] Step 5 — `documents` app: Document list, create, detail/hub views + templates
- [ ] Step 6 — `documents` app: Wizard (Alpine.js, 7 steps, story parsing)
- [ ] Step 7 — `documents` app: AI services (OpenAI integration, prompts)
- [ ] Step 8 — `documents` app: Court lookup (copy court_data/, wire into wizard step 3)
- [ ] Step 9 — `documents` app: Final review + PDF generation (WeasyPrint)
- [ ] Step 10 — `documents` app: Video evidence (subscribers only)
- [ ] Step 11 — `public_pages` app: CMS, landing page, info pages
- [ ] Step 12 — Polish: dark mode, SEO, sitemaps, Render deploy config

---

## Reference Repo
No reference repo is available in this environment. Build everything from this spec.

When the spec says "copy from old repo", interpret it as:
- **Theme CSS** — recreate `static/css/app-theme.css` using the color palette and design notes above
- **SVG logos** — recreate simple SVG gavel icons (gavel-icon.svg, gavel-logo.svg, gavel.svg, favicon.svg)
- **Court data** — recreate `documents/services/court_data/` with static city→court mappings per state, or stub it and rely on the GPT fallback until data is sourced
- **Context processor** — build from the spec description above
- **AI service** — build from the spec description above

Do not copy old wizard templates or section_edit templates — those are the old process being replaced.
