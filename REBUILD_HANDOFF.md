# 1983 Law — Rebuild Handoff

## The App
A Django web app at **file1983.com** that guides users through building a **Section 1983 civil rights complaint**
against government officials. Target users are **First Amendment auditors** and citizens documenting
police misconduct, unlawful arrest, excessive force, and retaliation for recording in public.

Flow: User tells their story (typed or spoken) → AI extracts structured data → wizard lets user
review/edit each section → final review → PDF download.

---

## Stack
- **Backend:** Django 4.2+, PostgreSQL (prod), SQLite (dev)
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, Playfair Display (Google Font), Alpine.js
- **AI:** OpenAI API (GPT-4) — story extraction, section generation, court lookup fallback
- **Payments:** Stripe — one-time purchases + subscriptions + webhooks
- **PDF:** WeasyPrint
- **Video Evidence:** Supadata API (YouTube transcript extraction)
- **Hosting:** Render (gunicorn + whitenoise)
- **Auth:** Custom User model, email-based (no username)
- **API:** Django REST Framework + SimpleJWT (wired up, endpoints stubbed for future mobile app)

---

## Design
- Color palette, navbar, footer, theme CSS already in place — do not redesign
- Master theme: `static/css/app-theme.css`
- SVG logos in `static/images/` (gavel-icon.svg, gavel-logo.svg, favicon.svg)
- Fonts: Playfair Display headings, system-ui body
- Dark mode toggle built into base.html, persisted via localStorage

---

## What's Been Built

### Project scaffold (`config/`)
- `config/settings.py` — full settings, env-based, SQLite dev / Postgres prod
- `config/urls.py` — includes accounts, documents, public_pages, api/v1/
- `config/context_processors.py` — injects `app_name`, `header_app_name`, `ADMIN_URL` into all templates
- `config/api_urls.py` — `/api/v1/token/`, `/api/v1/token/refresh/` (JWT)
- `base.html` — navbar, footer, dark mode, Bootstrap 5.3, Alpine.js, Bootstrap Icons
- Dynamic admin URL via `ADMIN_URL` env var (default: `manage-dev/`)

### `accounts/` app
**Models** (migrated):
- `User` — email-based auth. Includes `first_name`, `last_name`, `phone`, `address`, `city`, `state`, `zip_code`, `user_type` (plaintiff/attorney), `referral_code`, `referred_by`
  - `get_plaintiff_defaults()` → dict mapping directly to `PlaintiffInfo` fields
  - `has_complete_profile()` → bool (requires first_name, last_name, address, city, state)
  - `has_active_subscription()`, `has_unlimited_access()`, `get_ai_uses_remaining()`, `can_create_document()`
- `Subscription` — Stripe subscription (monthly/annual), status, period dates
- `DocumentPack` — one-time purchase credits (single/$49, 3-pack/$99)
- `SiteSettings` — singleton: app_name, pricing values, feature flags (registration_open, maintenance_mode)
- `LegalDocument` — terms/privacy/disclaimer pages (HTML content, managed via admin)

**Views/URLs** (all working):
- `/accounts/register/`, `/accounts/login/`, `/accounts/logout/`
- `/accounts/profile/` — edits all user fields including address; shows incomplete-profile warning banner; accepts `?next=` param and redirects there after save
- `/accounts/pricing/` — stub page ("coming soon"), ready for Stripe integration
- Full password reset flow (Django built-ins with custom templates)

**Forms:** `RegisterForm`, `LoginForm`, `ProfileForm` (all address fields), password reset forms

**Templates** (all working): login, register, profile, pricing (stub), password reset flow

**Still needed:**
- Stripe checkout session creation (single doc + subscription plans)
- Stripe webhook handler at `/accounts/subscription/webhook/`
- Real pricing page with plan cards

---

### `documents/` app

**Models** (migrated — `0001_initial.py`, `0002_examplestory.py`):

#### Document (root)
| Field | Type | Notes |
|---|---|---|
| `slug` | CharField | Short random URL-safe ID (e.g. `nP27cOkr`), auto-generated, immutable |
| `title` | CharField | Short user label |
| `payment_status` | CharField | draft / paid / finalized / expired |
| `jury_trial_demand` | BooleanField | Included in complaint header |

#### WizardSession (AI pipeline state)
| Field | Type | Notes |
|---|---|---|
| `story_text` | TextField | Raw story typed or dictated by user |
| `ai_analysis` | JSONField | Full structured output from GPT — see shape below |
| `status` | CharField | not_started / in_progress / analyzed / completed |
| `current_step` | SmallInt | 0=story, 1–7=wizard steps |
| `ai_extraction_attempted` | BooleanField | |
| `ai_extraction_succeeded` | BooleanField | |
| `ai_extraction_error` | TextField | Error message if extraction failed |

#### PlaintiffInfo → goes into complaint caption
`full_name`, `address`, `city`, `state`, `zip_code`, `phone`, `email`,
`filing_pro_se`, `attorney_name`, `attorney_bar_number`, `attorney_address`

#### IncidentOverview → jurisdiction + facts intro
`incident_date`, `incident_time`, `address`, `city`, `state`, `county`,
`location_description`, `location_type`, `is_public_forum`,
`plaintiff_activity`, `plaintiff_identified_themselves`, `identification_description`,
`force_used`, `equipment_seized_or_damaged`,
`federal_district_court`, `court_confirmed`

#### TimelineEntry → factual allegations (numbered paragraphs)
`order`, `time_approximate`, `actor`, `action_description`
*(multiple per document — each becomes a numbered paragraph in the complaint)*

#### Defendant → defendants section + caption
`full_name`, `badge_number`, `rank_title`, `agency_name`,
`parent_government_entity`, `agency_address`,
`capacity_sued` (individual/official/both),
`acting_under_color_of_law`, `color_of_law_basis`, `is_supervisor`
*(multiple per document)*

#### GovernmentEntity → Monell claim section
`entity_name`, `entity_address`, `policy_or_custom_description`

#### ConstitutionalClaim → causes of action
`amendment` (choices: 1st retaliation, 1st prior restraint, 1st viewpoint, 4th search,
4th seizure, 4th excessive force, 5th due process, 8th cruel, 14th due process,
14th equal protection, other), `how_violated`
*(multiple per document)*

#### Evidence → exhibits / supporting facts
`evidence_type` (video/photo/police_report/body_cam/foia/citation/medical/physical/document),
`description`, `date_and_time`, `recorded_by`, `storage_location`, `public_url`,
`defendant_aware_of_recording`
*(multiple per document)*

#### Witness → witness list
`full_name`, `contact_info`, `relationship_to_plaintiff`,
`what_they_witnessed`, `has_video`, `willing_to_testify`
*(multiple per document)*

#### Damages → damages section
`physical_injury_description`, `emotional_distress_description`,
`lost_wages` (decimal), `property_damage_amount` (decimal), `punitive_basis`

#### PriorComplaints → pattern of conduct / notice
`filed_complaints` (bool), `description`, `outcomes`

#### ReliefSought → prayer for relief
`compensatory_damages` (bool), `compensatory_amount` (decimal),
`punitive_damages`, `declaratory_judgment`, `injunctive_relief`,
`attorney_fees`, `costs_of_suit`, `other_relief`

#### Supporting models (dormant until those features are built)
- `AIPrompt` — admin-managed system/user prompt templates per task
- `PromoCode`, `PromoCodeUsage`, `PayoutRequest` — referral/discount system
- `ExampleStory` — test scenarios for staff dropdown on story page

---

**ai_analysis JSON shape** (what GPT must return — documented in full at top of `documents/models.py`):
```json
{
  "document": { "title": "", "jury_trial_demand": true },
  "plaintiff": { "full_name": "", "address": "", "city": "", "state": "", "zip_code": "", "phone": "", "email": "", "filing_pro_se": true, "attorney_name": "", "attorney_bar_number": "", "attorney_address": "" },
  "incident": { "incident_date": "YYYY-MM-DD", "incident_time": "HH:MM", "address": "", "city": "", "state": "", "county": "", "location_description": "", "location_type": "", "is_public_forum": null, "plaintiff_activity": "", "plaintiff_identified_themselves": null, "identification_description": "", "force_used": null, "equipment_seized_or_damaged": null, "federal_district_court": "" },
  "timeline": [ { "order": 1, "time_approximate": "", "actor": "", "action_description": "" } ],
  "defendants": [ { "full_name": "", "badge_number": "", "rank_title": "", "agency_name": "", "parent_government_entity": "", "agency_address": "", "capacity_sued": "both", "acting_under_color_of_law": true, "color_of_law_basis": "", "is_supervisor": false } ],
  "government_entity": { "entity_name": "", "entity_address": "", "policy_or_custom_description": "" },
  "constitutional_claims": [ { "amendment": "", "how_violated": "" } ],
  "evidence": [ { "evidence_type": "", "description": "", "date_and_time": "", "recorded_by": "", "storage_location": "", "public_url": "", "defendant_aware_of_recording": null } ],
  "witnesses": [ { "full_name": "", "contact_info": "", "relationship_to_plaintiff": "", "what_they_witnessed": "", "has_video": null, "willing_to_testify": null } ],
  "damages": { "physical_injury_description": "", "emotional_distress_description": "", "lost_wages": null, "property_damage_amount": null, "punitive_basis": "" },
  "relief": { "compensatory_damages": false, "compensatory_amount": null, "punitive_damages": false, "declaratory_judgment": false, "injunctive_relief": false, "attorney_fees": false, "costs_of_suit": false, "other_relief": "" },
  "prior_complaints": { "filed_complaints": false, "description": "", "outcomes": "" }
}
```

**Views/URLs** (working):
- `GET /documents/` → document list
- `GET /documents/new/` → profile gate → create Document + WizardSession + PlaintiffInfo → redirect to wizard
- `GET/POST /documents/<slug>/wizard/` → story input page

**Templates** (working):
- `documents/list.html` — stub (needs building)
- `documents/wizard_story.html` — story textarea, word count, Save + Analyze buttons, staff/DEBUG example story dropdown (Alpine.js fills textarea on selection)

**Example stories fixture:** `documents/fixtures/example_stories.json`
10 First Amendment auditor scenarios. Load with:
`python manage.py loaddata example_stories`

---

## ⬅️ NEXT STEP: GPT Story Extraction Service

Build `documents/services/openai_service.py`.

### What it needs to do:
1. Take `WizardSession.story_text` as input
2. Call GPT-4 with a system prompt instructing it to extract structured data
3. Return JSON matching the `ai_analysis` shape above
4. Save that JSON to `WizardSession.ai_analysis`
5. Populate all related models from the JSON:
   - Update `PlaintiffInfo` (already exists, created from user profile — merge/update don't overwrite)
   - Create/update `IncidentOverview`
   - Create `TimelineEntry` records (delete old ones first)
   - Create `Defendant` records (delete old ones first)
   - Create/update `GovernmentEntity`
   - Create `ConstitutionalClaim` records (delete old ones first)
   - Create `Evidence` records (delete old ones first)
   - Create `Witness` records (delete old ones first)
   - Create/update `Damages`
   - Create/update `PriorComplaints`
   - Create/update `ReliefSought`
   - Update `Document.title` if GPT provided one
6. Set `WizardSession.ai_extraction_succeeded = True` (or False + error message)
7. Set `WizardSession.status = 'analyzed'`

### Where it gets called:
`documents/views.py` → `wizard_story` view → when `action == 'analyze'` in POST

### Key implementation notes:
- Run extraction synchronously for now (async/Celery is future work)
- The system prompt should tell GPT: extract only what is explicitly stated, use null for unknown fields, return valid JSON only
- PlaintiffInfo is pre-populated from user profile — only overwrite fields where GPT found something more specific (e.g. if user mentioned a different address in their story)
- All model creates should use `get_or_create` / `update_or_create` so re-analyzing the same story doesn't create duplicates
- After extraction succeeds, redirect to Step 1 (plaintiff review) — not yet built
- The `AIPrompt` model in admin can hold the system prompt — check for an active `story_parse` prompt first, fall back to a hardcoded default

### Suggested GPT system prompt direction:
> You are a legal document assistant helping build a Section 1983 civil rights complaint.
> Extract structured information from the user's story. Return only valid JSON matching the provided schema.
> Use null for any field not mentioned. Do not invent details not in the story.
> For constitutional claims, identify which amendments were likely violated based on the facts described.
> For the timeline, break events into discrete chronological steps, one action per entry.

---

## URL Map (current)
```
/                          → public_pages:home (stub)
/accounts/register/        → register
/accounts/login/           → login
/accounts/logout/          → logout
/accounts/profile/         → profile (full address fields, incomplete-profile banner)
/accounts/pricing/         → pricing stub
/accounts/password-reset/  → password reset flow
/documents/                → document list (stub template)
/documents/new/            → create document (profile gate)
/documents/<slug>/wizard/  → story input page ← user is here
/api/v1/token/             → JWT obtain
/api/v1/token/refresh/     → JWT refresh
/<ADMIN_URL>/              → Django admin
```

---

## Docker / Dev Setup
```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata example_stories
docker compose exec web python manage.py createsuperuser
```

Database is `file1983` on the `db` service (postgres:16).
Connect directly: `docker compose exec db psql -U postgres -d file1983`

---

## Environment Variables
```
SECRET_KEY=
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@db:5432/file1983
ADMIN_URL=manage-dev/
OPENAI_API_KEY=                ← needed for next step
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
- [x] Project scaffold — settings, URLs, base template, theme CSS, dark mode, DRF+JWT
- [x] `accounts` app — User model (with address/profile), auth views, profile page, password reset
- [x] `accounts` app — pricing stub (real Stripe checkout deferred)
- [x] `documents` app — all models + admin + migrations
- [x] `documents` app — document create (profile gate, auto-create PlaintiffInfo from user profile)
- [x] `documents` app — wizard story page (Save + Analyze buttons, example stories dropdown)
- [ ] **`documents` app — GPT extraction service** ← BUILD THIS NEXT
- [ ] `documents` app — wizard steps 1–7 (review/edit extracted fields)
- [ ] `documents` app — document list template
- [ ] `documents` app — court lookup service (city+state → federal district court)
- [ ] `documents` app — final review page + PDF generation (WeasyPrint)
- [ ] `documents` app — video evidence (Supadata API, subscribers only)
- [ ] `accounts` app — Stripe checkout + webhooks
- [ ] `public_pages` app — landing page CMS
- [ ] Deploy config — Render, gunicorn, whitenoise, sitemaps

---

## Key Decisions Already Made
- `Document` (not `Complaint`) is the root model — owns the slug and payment state
- All wizard model fields are `blank=True` / `null=True` — partial AI extraction must not break anything
- `User` stores address directly (no separate Profile model) — `get_plaintiff_defaults()` pre-populates `PlaintiffInfo`
- `user_type` on User (`plaintiff`/`attorney`) future-proofs attorney account linking
- `TimelineEntry` (ordered, multiple) is the factual allegations section — better than a single text blob
- `ExampleStory` dropdown only shown to `is_staff` or `DEBUG=True`
- Slugs are immutable once set — never regenerate on update
- Document ownership enforced on every view: `get_object_or_404(Document, slug=slug, user=request.user)`
