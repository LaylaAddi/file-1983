# 1983 Law — Clean Rebuild Handoff

## What This Is
A step-by-step rebuild of 1983law.org from scratch. Same stack, clean database, cleaner code.
Build everything from this spec. Nothing is copied from an old codebase.

---

## The App
A Django web app at **file1983.com** that guides users through building a **Section 1983 civil rights complaint**
against government officials. Users tell their story, the AI analyzes it, and the wizard walks
them through steps to produce a complete legal document (PDF).

Target users: **First Amendment auditors** and citizens documenting civil rights violations
(police misconduct, unlawful arrest, excessive force, retaliation for recording in public).

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
Stored in `static/images/`:
- `gavel-icon.svg` — navbar icon (24x24 in a rounded box)
- `gavel-logo.svg` — full logo
- `gavel.svg` — standalone gavel
- `favicon.svg` — browser tab icon

### Fonts
- **Headings:** Playfair Display (600, 700) — loaded from Google Fonts
- **Body:** system-ui stack

### Theme CSS
`static/css/app-theme.css` is the master theme file. Already in place.

---

## Django Apps

### `config/`
- Settings in `config/settings.py`
- Dynamic admin URL: `ADMIN_URL = os.getenv('ADMIN_URL', 'manage-dev/')`
- Context processor: `config/context_processors.py` — injects `app_name`, `header_app_name`, `user`, `ADMIN_URL`
- `base.html` with navbar, footer, dark mode toggle, Bootstrap 5.3 + Alpine.js

### `accounts/`
**Models** (all built, migrated):
- `User` — custom email-based auth. Fields include `first_name`, `last_name`, `phone`, `address`, `city`, `state`, `zip_code`, `user_type` (plaintiff/attorney), `referral_code`, `referred_by`
  - `get_plaintiff_defaults()` → dict that maps to `PlaintiffInfo` fields, used to pre-populate on document creation
  - `has_complete_profile()` → bool, gates document creation
  - `has_active_subscription()`, `has_unlimited_access()`, `get_ai_uses_remaining()`, `can_create_document()`
- `Subscription` — Stripe subscription tracking
- `DocumentPack` — one-time purchase credits
- `SiteSettings` — singleton (app_name, pricing, feature flags)
- `LegalDocument` — terms/privacy pages

**Views** (all built):
- `register`, `user_login`, `user_logout`, `profile`
- Profile view accepts `?next=` param — redirects there after save (used for profile gate)
- Password reset flow (Django built-ins)

**Forms:** `RegisterForm`, `LoginForm`, `ProfileForm` (includes all address fields), `CustomPasswordResetForm`, `CustomSetPasswordForm`

**Templates** (all built): login, register, profile (with incomplete profile banner), password reset flow

**Still needed in accounts:**
- `pricing` view and template (Stripe checkout)
- Stripe webhook handler at `/accounts/subscription/webhook/`

---

### `documents/`

**Models** (all built — `documents/migrations/0001_initial.py`, `0002_examplestory.py`):

| Model | Relation | Description |
|---|---|---|
| `Document` | root | slug (short random, URL-safe), user FK, title, payment_status, jury_trial_demand |
| `WizardSession` | 1-to-1 | story_text, ai_analysis (JSON), current_step, status, ai_extraction flags |
| `PlaintiffInfo` | 1-to-1 | name, address, phone, email, filing_pro_se, attorney fields |
| `IncidentOverview` | 1-to-1 | date, time, address, location_type, is_public_forum, plaintiff_activity, force_used, court fields |
| `TimelineEntry` | FK (multiple) | ordered events extracted from story (order, time_approximate, actor, action_description) |
| `Defendant` | FK (multiple) | name, badge, rank, agency, parent_gov_entity, capacity_sued, acting_under_color_of_law, is_supervisor |
| `GovernmentEntity` | 1-to-1 | Monell claim — entity name/address, policy_or_custom_description |
| `ConstitutionalClaim` | FK (multiple) | amendment (detailed choices incl. retaliation, prior restraint), how_violated |
| `Evidence` | FK (multiple) | type, description, recorded_by, public_url, defendant_aware_of_recording, file upload |
| `Witness` | FK (multiple) | name, contact, relationship, what_they_witnessed, has_video, willing_to_testify |
| `Damages` | 1-to-1 | physical, emotional, lost_wages (decimal), property_damage (decimal), punitive_basis |
| `PriorComplaints` | 1-to-1 | filed_complaints (bool), description, outcomes |
| `ReliefSought` | 1-to-1 | checkboxes + compensatory_amount, costs_of_suit |
| `AIPrompt` | standalone | admin-managed prompts per AI task (task_name, system_prompt, user_prompt_template) |
| `PromoCode` | standalone | discount codes with expiry and use limits |
| `PromoCodeUsage` | FK | tracks which user used which code |
| `PayoutRequest` | FK | referral payout tracking |
| `ExampleStory` | standalone | test scenarios for staff/DEBUG dropdown on story input page |

**AI Analysis JSON shape** is documented at the top of `documents/models.py`. The `WizardSession.ai_analysis` field stores AI extraction output keyed to match every model above. When AI runs, it returns this shape; wizard steps read from it to pre-populate forms.

**Views** (partially built):
- `document_list` — lists user's documents
- `document_create` — gates on `has_complete_profile()`, creates Document + WizardSession + PlaintiffInfo (pre-populated from user profile), redirects to wizard_story
- `wizard_story` — Step 0: story input page, saves story_text to WizardSession

**URLs:**
- `/documents/` → `document_list`
- `/documents/new/` → `document_create`
- `/documents/<slug>/wizard/` → `wizard_story`

**Templates:**
- `documents/list.html` — stub, needs building
- `documents/wizard_story.html` — **built**: story textarea, word count, example stories dropdown (staff/DEBUG only), "Analyze My Story" submit button

**Example Stories fixture:** `documents/fixtures/example_stories.json`
Load with: `python manage.py loaddata example_stories`
10 First Amendment auditor scenarios: recording at police station, library, city hall, courthouse, DMV, city council meeting, traffic stop, protest, park. Each detailed enough to exercise full AI extraction.

**Still needed in documents (build in this order):**
1. AI extraction service (`documents/services/openai_service.py`) — called after story submit, writes to `WizardSession.ai_analysis`, creates/updates related models
2. Wizard steps 1–7 views + templates (review/edit what AI extracted)
3. Court lookup service (`documents/services/court_lookup_service.py`) — city+state → federal district court
4. Final review view + template
5. PDF generation (`documents/services/pdf_service.py` — WeasyPrint)
6. Video evidence view (Supadata API, subscribers only)
7. AJAX endpoints for step saves and AI calls

**Wizard flow (complete picture):**
```
/documents/new/
  → profile gate (redirect to profile if incomplete)
  → create Document + WizardSession + PlaintiffInfo
  → redirect to /documents/<slug>/wizard/

/documents/<slug>/wizard/  (Step 0 — built)
  → user types or dictates story
  → staff/DEBUG: example story dropdown pre-fills textarea
  → submit → save story_text → trigger AI extraction
  → redirect to Step 1

Steps 1–7 (not yet built — one URL each or single Alpine.js SPA):
  Step 1: Review/edit Plaintiff Info
  Step 2: Review/edit Incident Overview + Timeline
  Step 3: Review/edit Defendants + Government Entity
  Step 4: Review/edit Constitutional Claims
  Step 5: Review/edit Evidence + Witnesses
  Step 6: Review/edit Damages + Relief
  Step 7: Final review → "Build Complaint" → PDF
```

---

### `public_pages/`
- Not yet built
- Models: `CivilRightsPage`, `PageSection`
- Section types: hero, cards, quotes, CTAs, accordions
- URLs: `/` (home), `/page/<slug>/`

---

## Federal Court Lookup
Two-tier:
1. Static lookup — `court_lookup_service.py` imports state module from `documents/services/court_data/states/`
2. GPT fallback — if city not found, calls `openai_service.lookup_federal_court(city, state)`
- Not yet built. Stub `court_data/` or rely on GPT fallback initially.

---

## Slugs
- `Document` uses short random slug (`secrets.token_urlsafe(6)`), collision-checked, set on first save, never regenerated
- All document URLs use `<str:document_slug>/`

---

## Mobile API (wired, not yet built out)
- `rest_framework` + `simplejwt` installed and in INSTALLED_APPS
- `/api/v1/` namespace in `config/urls.py`
- JWT settings in `settings.py`
- Token endpoints: `/api/v1/token/`, `/api/v1/token/refresh/`
- API views to build alongside web features (stub → implement):
  - `POST /api/v1/auth/register/`
  - `POST /api/v1/auth/login/`
  - `GET/POST /api/v1/documents/`
  - `GET /api/v1/documents/<slug>/`
  - `POST /api/v1/documents/<slug>/wizard/save/`
  - `POST /api/v1/documents/<slug>/wizard/analyze/`

---

## Security
- Dynamic admin URL via `ADMIN_URL` env var
- CSRF on all forms
- Login required on all document views
- Document ownership check: `get_object_or_404(Document, slug=slug, user=request.user)`
- Stripe webhook signature verification (not yet built)

---

## Environment Variables
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

## Build Status

- [x] Step 1 — Project scaffold (Django project, apps, settings, base template, theme CSS, DRF + JWT)
- [x] Step 2 — `accounts` app: User model (with address/profile fields), auth views, login/register/profile templates
- [ ] Step 3 — `accounts` app: Stripe pricing page + checkout + webhooks ← **NEXT**
- [x] Step 4a — `documents` app: All models + migrations + admin
- [x] Step 4b — `documents` app: document_create view (profile gate), wizard_story view + template, example stories fixture
- [ ] Step 4c — `documents` app: AI extraction service (openai_service.py) — story → structured JSON → populate models
- [ ] Step 4d — `documents` app: Wizard steps 1–7 (review/edit forms, Alpine.js)
- [ ] Step 4e — `documents` app: Court lookup service
- [ ] Step 4f — `documents` app: Document list + detail/hub views + templates
- [ ] Step 5 — `documents` app: Final review + PDF generation (WeasyPrint)
- [ ] Step 6 — `documents` app: Video evidence (Supadata, subscribers only)
- [ ] Step 7 — `public_pages` app: CMS, landing page, info pages
- [ ] Step 8 — Polish: SEO, sitemaps, Render deploy config

---

## Key Decisions Made
- Root model is `Document` (not `Complaint`) — owns the slug and payment state
- `WizardSession` stores raw story + AI JSON — separate from the structured models it populates
- All wizard models have `blank=True` / `null=True` on most fields — AI partial extraction must not break the form
- `User` stores address/contact directly (no separate Profile model) — `get_plaintiff_defaults()` maps to `PlaintiffInfo`
- `user_type` field on User (`plaintiff` / `attorney`) future-proofs attorney account flow
- `ExampleStory` model is admin-managed; fixture has 10 auditor scenarios; dropdown only shown to `is_staff` or `DEBUG=True`
- `TimelineEntry` (ordered events) replaces single narrative blob — better for AI extraction and PDF factual allegations section
- `ConstitutionalClaim` has granular amendment choices including 1st Amendment retaliation, prior restraint, viewpoint discrimination
- `GovernmentEntity` model handles Monell municipal liability theory

---

## Reference Repo
No reference repo available. Build from this spec.

When spec says "copy from old repo":
- **Theme CSS** — `static/css/app-theme.css` already in place
- **SVG logos** — `static/images/` already has gavel SVGs
- **Court data** — recreate or stub `documents/services/court_data/` with city→court mappings; GPT fallback covers gaps
- **AI service** — build from spec description
