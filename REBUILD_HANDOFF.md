# 1983 Law — Project Handoff

## The App
A Django web app that guides users through building a **Section 1983 civil rights complaint**
against government officials. Target users: First Amendment auditors, citizens documenting
police misconduct, unlawful arrest, excessive force, retaliation for recording in public.

Flow: User tells their story → AI extracts structured data → wizard lets user review/edit
each section → final review → PDF download → Stripe payment to unlock.

---

## Git Setup

### Pull latest to local
```bash
git fetch origin
git checkout claude/test-gpt-story-extraction-dZ5XG
git pull origin claude/test-gpt-story-extraction-dZ5XG
```

### Push to master when done
```bash
git checkout master
git merge claude/test-gpt-story-extraction-dZ5XG
git push origin master
```

### Development branch
All new work goes on: `claude/test-gpt-story-extraction-dZ5XG`

---

## Stack
- **Backend:** Django 4.2+, PostgreSQL
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, Playfair Display, Alpine.js
- **AI:** OpenAI GPT-4o — story extraction + court lookup fallback
- **Payments:** Stripe (not yet wired)
- **PDF:** WeasyPrint (not yet wired)
- **Auth:** Custom User model, email-based (no username)

---

## Docker Dev Setup
```bash
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata example_stories
docker compose exec web python manage.py createsuperuser
```

Restart detached after stopping:
```bash
docker compose up -d
```

View logs:
```bash
docker compose logs -f web
```

Database: `file1983` on the `db` service (postgres:16)
Direct DB access: `docker compose exec db psql -U postgres -d file1983`

---

## Environment Variables (`.env` file)
```
SECRET_KEY=
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@db:5432/file1983
ADMIN_URL=manage-dev/
OPENAI_API_KEY=              ← required for extraction + court lookup fallback
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
```

---

## URL Map
```
/                                          → public_pages:home (stub)
/accounts/register/                        → register
/accounts/login/                           → login
/accounts/logout/                          → logout
/accounts/profile/                         → profile (full address, incomplete-profile banner)
/accounts/pricing/                         → pricing stub
/accounts/password-reset/                  → password reset flow
/documents/                                → document list
/documents/new/                            → create document (profile gate)
/documents/<slug>/wizard/                  → story input page
/documents/<slug>/wizard/summary/          → post-extraction summary (found/missing review)
/documents/<slug>/wizard/step1/            → Step 1: federal jurisdiction / court confirmation
/documents/<slug>/wizard/step2/            → Step 2: incident details (date, location, activity, force)
/documents/lookup-district-court/          → AJAX: GET ?city=&state= → court name JSON
/api/v1/token/                             → JWT obtain
/api/v1/token/refresh/                     → JWT refresh
/<ADMIN_URL>/                              → Django admin
```

---

## Build Status
- [x] Project scaffold — settings, URLs, base template, theme CSS, dark mode, DRF+JWT
- [x] `accounts` — User model (address/profile fields), auth views, profile page, password reset
- [x] `documents` — all models + admin + migrations
- [x] `documents` — document create view (profile gate, auto-create PlaintiffInfo from user profile)
- [x] `documents` — document list page (title, status badge, wizard progress, story preview)
- [x] `documents` — wizard story page (Save + Analyze, inline progress animation, example stories dropdown)
- [x] `documents` — GPT extraction service (`documents/services/openai_service.py`)
- [x] `documents` — court lookup service (`documents/services/court_lookup_service.py`) — static city maps + GPT fallback
- [x] `documents` — post-extraction summary page (found/partial/missing per category, red/yellow/green banner)
- [x] `documents` — Step 1: federal jurisdiction only (auto-populate court, confirm checkbox, manual override)
- [x] `documents` — example stories fixture (PKs 1–10 complete, PKs 11–14 gap-test stories)
- [x] `documents` — Step 2: incident details form (date, location, activity, force/equipment, court-clearing on city/state change)
- [ ] **Step 3: Defendants (add/edit/delete, multi-record)** ← BUILD NEXT
- [ ] Step 4: Constitutional claims (multi-record)
- [ ] Step 5: Evidence & Witnesses (multi-record)
- [ ] Step 6: Damages & Relief
- [ ] Step 7: Final review
- [ ] PDF generation (WeasyPrint)
- [ ] Stripe payment integration
- [ ] Landing page CMS (`public_pages`)
- [ ] Deploy config (Render, gunicorn, whitenoise)

---

## What's Built — Detail

### Wizard Flow (current)
1. User goes to `/documents/new/` → profile gate → Document + WizardSession + PlaintiffInfo created
2. Story page (`wizard_story`) — user types story, clicks Analyze
   - Alpine.js inline progress animation plays (7-step fake progress, 1.8s per step)
   - POST → `_gpt_test()` → calls `extract_story(session, dry_run=False)`
   - Full extraction printed to terminal (`docker compose logs -f web`)
   - Redirects to summary page
3. Summary page (`wizard_extraction_summary`) — shows what GPT found vs missed
   - Red banner if critical fields missing (date, location, defendants, claims)
   - Yellow banner if minor gaps
   - Green banner if mostly complete
   - Each category: icon + found/partial/missing status + detail text
   - "Improve My Story" → back; "Continue to Review" / "Continue Anyway" → Step 1
4. Step 1 (`wizard_step1`) — federal jurisdiction only
   - Court auto-populated from city+state via `CourtLookupService`
   - User confirms with checkbox, or clicks "This is wrong" to override
   - AJAX lookup at `/documents/lookup-district-court/` if manual re-lookup needed
   - POST saves `federal_district_court` + `court_confirmed = True` to `IncidentOverview`
   - On success → redirects to Step 2
5. Step 2 (`wizard_step2`) — incident details
   - Pre-populated from GPT extraction; user reviews/edits all fields
   - Fields: date, time, address, city, state, county, location description, location type, public forum, plaintiff activity, force used, equipment seized
   - If city or state changes: clears `federal_district_court` and `court_confirmed=False`, redirects back to Step 1
   - On save: advances `current_step` to 3, redirects to Step 3 (placeholder until built)
   - Reusable progress indicator: `templates/documents/_wizard_progress.html`

### GPT Extraction (`documents/services/openai_service.py`)
- `extract_story(session, dry_run=False)` — calls GPT-4o, parses JSON, calls `_populate_models()`
- `_populate_models()` — writes all wizard models from `ai_analysis` JSON:
  - Always resets `federal_district_court=''` and `court_confirmed=False` on re-analysis
  - Deletes and recreates: TimelineEntry, Defendant, ConstitutionalClaim, Evidence, Witness
  - Update-or-create: PlaintiffInfo, IncidentOverview, GovernmentEntity, Damages, PriorComplaints, ReliefSought
  - Updates Document.title if GPT provided one

### Court Lookup (`documents/services/court_lookup_service.py`)
- `CourtLookupService.lookup_court_by_location(city, state)`
- Three-tier: static city map → state-level fallback → GPT-4o fallback
- State files in `documents/services/court_data/states/` (54 files, all states + DC + territories)
- Handles full state names ("Florida") via `STATE_NAME_TO_CODE` normalization
- GPT fallback uses direct `openai.OpenAI()` client (not the extraction service)

### Models — Key Notes
- `Damages.lost_wages` and `property_damage_amount` are **TextField** (not Decimal) — GPT returns strings like "Missed a work shift"
- `WizardSession.ai_extraction_succeeded` controls which state the story page renders
- All wizard model fields are `blank=True` / `null=True` — partial extraction never breaks anything
- Document ownership enforced on every view: `get_object_or_404(Document, slug=slug, user=request.user)`

### `ai_analysis` JSON shape (what GPT returns, stored in `WizardSession.ai_analysis`):
```json
{
  "document": { "title": "", "jury_trial_demand": true },
  "plaintiff": { "full_name": "", "address": "", "city": "", "state": "", "zip_code": "", "phone": "", "email": "", "filing_pro_se": true },
  "incident": { "incident_date": "YYYY-MM-DD", "incident_time": "HH:MM", "address": "", "city": "", "state": "", "county": "", "location_description": "", "location_type": "", "is_public_forum": null, "plaintiff_activity": "", "force_used": null, "equipment_seized_or_damaged": null },
  "timeline": [ { "order": 1, "time_approximate": "", "actor": "", "action_description": "" } ],
  "defendants": [ { "full_name": "", "badge_number": "", "rank_title": "", "agency_name": "", "capacity_sued": "both", "acting_under_color_of_law": true, "is_supervisor": false } ],
  "government_entity": { "entity_name": "", "entity_address": "", "policy_or_custom_description": "" },
  "constitutional_claims": [ { "amendment": "", "how_violated": "" } ],
  "evidence": [ { "evidence_type": "", "description": "", "date_and_time": "", "recorded_by": "", "public_url": "", "defendant_aware_of_recording": null } ],
  "witnesses": [ { "full_name": "", "contact_info": "", "relationship_to_plaintiff": "", "what_they_witnessed": "", "has_video": null, "willing_to_testify": null } ],
  "damages": { "physical_injury_description": "", "emotional_distress_description": "", "lost_wages": null, "property_damage_amount": null, "punitive_basis": "" },
  "relief": { "compensatory_damages": false, "punitive_damages": false, "declaratory_judgment": false, "injunctive_relief": false, "attorney_fees": false, "costs_of_suit": false },
  "prior_complaints": { "filed_complaints": false, "description": "", "outcomes": "" }
}
```

### Example Stories Fixture (`documents/fixtures/example_stories.json`)
- PKs 1–10: complete well-formed First Amendment auditor stories (various cities/states)
- PKs 11–14: gap-test stories with "(gaps in story)" in title:
  - PK 11: no location at all
  - PK 12: Nashville TN, no officer names or badge numbers
  - PK 13: Portland OR, named officers (Cole/Kim), no date, no damages
  - PK 14: extremely vague, almost nothing extractable

Load into DB: `docker compose exec web python manage.py loaddata example_stories`
Dropdown shows only for `is_staff` users or when `DEBUG=True`

---

## Next Step: Wizard Step 3 — Defendants

**URL:** `GET/POST /documents/<slug>/wizard/step3/`
**Models:** `Defendant` (multi-record, FK to Document) + `GovernmentEntity` (OneToOne)
**Template:** `templates/documents/wizard_step3.html`

### What it needs:
- List existing defendants (pre-populated from GPT extraction)
- Add / edit / delete individual defendants
- Each defendant: full_name, badge_number, rank_title, agency_name, capacity_sued, acting_under_color_of_law, is_supervisor
- Government entity section (Monell claim): entity_name, entity_address, policy_or_custom_description
- Navigation: back → Step 2, continue → Step 4
- On POST: save all, advance `session.current_step` to 4 if < 4
- Use `_wizard_progress.html` include with `current_step=3`

---

## Design Rules
- Do not redesign — color palette, navbar, footer, fonts are fixed
- Master theme: `static/css/app-theme.css`
- Headings use Playfair Display (`font-family:'Playfair Display',serif`)
- Alpine.js for all frontend interactivity (already loaded in base.html)
- Bootstrap 5.3 classes only — no custom CSS unless absolutely necessary
- Flash messages: use Django `messages` framework (already wired in base.html)
- Keep wizard steps focused — one decision per page, no overwhelming forms
