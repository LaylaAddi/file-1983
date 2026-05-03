# 1983 Law — Project Handoff

## The App
A Django web app that guides users through building a **Section 1983 civil rights complaint**
against government officials. Target users: First Amendment auditors, citizens documenting
police misconduct, unlawful arrest, excessive force, retaliation for recording in public.

Flow: User tells their story → AI extracts structured data → wizard lets user review/edit
each section → final review → AI drafts factual allegations → user reviews/edits draft → PDF download → Stripe payment to remove draft watermark.

---

## Git Setup

### Pull latest from master
```bash
git fetch origin
git checkout master
git pull origin master
```

### Workflow
All work goes on a new feature branch off master:
```bash
git checkout master && git pull origin master
git checkout -b claude/<short-description>
# ... make changes, commit ...
git push -u origin claude/<short-description>
git checkout master
git pull origin claude/<short-description>      # if branch isn't tracked locally
git push origin master
```

---

## Stack
- **Backend:** Django 4.2+, PostgreSQL
- **Frontend:** Bootstrap 5.3, Bootstrap Icons, Playfair Display, Alpine.js
- **AI:** OpenAI GPT-4o — story extraction, court lookup fallback, factual-allegations drafting
- **Payments:** Stripe (not yet wired)
- **PDF:** WeasyPrint (wired — Letter, 1in margins, Times 12pt, double-spaced, page footers)
- **Auth:** Custom User model, email-based (no username)
- **Deploy target:** Render (not yet deployed)

---

## Domains
- **`file1983.com`** — primary, the URL given to users
- **`auditfile1983.com`** — secondary, redirects to `file1983.com`
- Email: `rights@file1983.com` via Namecheap Private Email (`mail.privateemail.com`, port 587, TLS)

---

## Docker Dev Setup
```bash
docker compose build web         # only when Dockerfile changes
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata example_stories
docker compose exec web python manage.py loaddata foundational_case_law
docker compose exec web python manage.py createsuperuser
```

Database: `file1983` on the `db` service (postgres:16)
Direct DB access: `docker compose exec db psql -U postgres -d file1983`

Run the test suite (see Test Suite below):
```bash
docker compose exec web python manage.py test documents -v 2
```

---

## Environment Variables (`.env` file)
```
SECRET_KEY=
DEBUG=1
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@db:5432/file1983
ADMIN_URL=manage-dev/
OPENAI_API_KEY=                  ← required for extraction, court lookup fallback, draft generation
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_SINGLE=
STRIPE_PRICE_3PACK=
STRIPE_PRICE_MONTHLY=
STRIPE_PRICE_ANNUAL=
EMAIL_HOST=mail.privateemail.com
EMAIL_PORT=587
EMAIL_USE_TLS=1
EMAIL_HOST_USER=rights@file1983.com
EMAIL_HOST_PASSWORD='<wrap-in-single-quotes-if-special-chars>'
DEFAULT_FROM_EMAIL=rights@file1983.com
```

---

## URL Map
```
/                                           → public_pages:home (stub)
/accounts/register/                         → register
/accounts/login/                            → login
/accounts/logout/                           → logout
/accounts/profile/                          → profile (full address, incomplete-profile banner)
/accounts/pricing/                          → pricing stub
/accounts/password-reset/                   → password reset flow
/documents/                                 → document list (admin sees Delete button)
/documents/new/                             → create document (profile gate)
/documents/<slug>/delete/                   → POST-only, staff-only, deletes document
/documents/<slug>/wizard/                   → story input page
/documents/<slug>/wizard/summary/           → post-extraction summary (found/missing review)
/documents/<slug>/wizard/step1/             → Step 1: federal jurisdiction / court confirmation
/documents/<slug>/wizard/step2/             → Step 2: incident details (date, location, activity, force)
/documents/<slug>/wizard/step3/             → Step 3: defendants (add/edit/delete) + government entity
/documents/<slug>/wizard/step4/             → Step 4: constitutional claims (add/edit/delete)
/documents/<slug>/wizard/step5/             → Step 5: evidence & witnesses (multi-record, video timestamps)
/documents/<slug>/wizard/step6/             → Step 6: damages, relief, prior complaints
/documents/<slug>/wizard/step7/             → Step 7: final review (read-only with edit links)
/documents/<slug>/wizard/caselaw/           → Case law strategy choice (post-review, optional)
/documents/<slug>/wizard/draft/             → AI-drafted factual allegations + full complaint preview, editable
/documents/<slug>/wizard/generate/          → WeasyPrint PDF download (watermarked unless paid)
/documents/lookup-district-court/           → AJAX: GET ?city=&state= → court name JSON
/api/v1/token/                              → JWT obtain
/api/v1/token/refresh/                      → JWT refresh
/<ADMIN_URL>/                               → Django admin
```

---

## Build Status

### Done
- [x] Project scaffold — settings, URLs, base template, theme CSS, dark mode, DRF+JWT
- [x] `accounts` — User model (address/profile fields), auth views, profile page, password reset
- [x] `documents` — all models + admin + migrations
- [x] `documents` — document create view (profile gate, auto-create PlaintiffInfo from user profile)
- [x] `documents` — document list page (title, status badge, wizard progress, story preview); staff-only Delete button
- [x] `documents` — wizard story page (Save + Analyze, inline progress animation, example stories dropdown, bfcache reset on browser-back)
- [x] `documents` — GPT extraction service (`documents/services/openai_service.py`)
- [x] `documents` — court lookup service (`documents/services/court_lookup_service.py`) — static city maps + GPT fallback
- [x] `documents` — post-extraction summary page (found/partial/missing per category, red/yellow/green banner)
- [x] `documents` — Step 1: federal jurisdiction only (auto-populate court, confirm checkbox, manual override)
- [x] `documents` — example stories fixture (PKs 1–10 complete, PKs 11–14 gap-test stories)
- [x] `documents` — Step 2: incident details form (date, location, activity, force/equipment, court-clearing on city/state change)
- [x] `documents` — 27 grouped location types (police station lobby, courthouse, DMV, post office, etc.) with optgroup dropdown
- [x] `documents` — Step 3: defendants (Alpine.js dynamic add/edit/delete cards, government entity Monell section)
- [x] `documents` — Step 4: constitutional claims (add/edit/delete, duplicate-amendment protection)
- [x] `documents` — Step 4 guidance: plain-English amendment descriptions + examples per claim, attorney-consultation disclaimer, "Suggested from your story" badge on GPT-populated claims
- [x] `documents` — amendment normalization (`normalize_amendment()`) so GPT loose values like "First" map to canonical keys like `1st_retaliation`; applied in extraction and Step 4 render
- [x] `documents` — CaseLaw model + admin + 15 foundational cases fixture (now wired into draft + PDF)
- [x] `documents` — Step 5: evidence & witnesses (Alpine.js multi-record, two sections on one page); per-evidence **Key Timestamp** input (HH:MM:SS, period-to-colon auto-convert, `+`/`−` spinner buttons, 0-pad on blur) shown only for video/body_cam types
- [x] `documents` — Step 6: damages, relief sought, prior complaints (single-form, all OneToOne); **"Use recommended"** button checks the standard 1983 ask in one click; frequency badges (Standard / Common / Specific cases) next to each relief item
- [x] `documents` — Step 7: final review (read-only summary of every section with pencil-edit links back to each step). Shows the Case Law Strategy + auto-picked supporting cases when strategy ≠ `none`, and the video Key Timestamp with a "Starts at HH:MM:SS" badge linking directly to the deep-linked URL
- [x] `documents` — case law strategy chooser (`/wizard/<slug>/caselaw/`) — 4-option page (none / inline / memorandum / appendix) with pro-se / Twombly-Iqbal / Haines explanation; saved on `Document.caselaw_strategy`
- [x] `documents` — state code normalization (`normalize_state()` in openai_service) so GPT "Florida" → "FL" matches the Step 2 dropdown; self-heals existing rows on Step 1/2 render
- [x] `documents` — clickable wizard progress dots (`templates/documents/_wizard_progress.html`) — completed steps link to that page; gating uses `session.current_step` so previously-completed sections stay reachable when navigating back
- [x] `documents` — complaint draft page (`/wizard/<slug>/draft/`) with AI-drafted, user-editable factual allegations + full preview of the complaint (caption, jurisdiction, parties, **Supporting Evidence**, damages, prayer, signature, optional appendix/memorandum). "Case No. ___ (clerk assigns)" hint shown on draft preview only, not on PDF. Action bar: **Save edits**, **Re-draft from story** (confirms first), **Generate PDF**
- [x] `documents` — `complaint_drafter.py` GPT service that turns `story_text` + structured wizard data into numbered first-person factual allegations. Hard-rule prompt: no new facts, no legal characterization, no citations, plain English. Returns `{"paragraphs": [...]}`. Cached on `Document.factual_allegations_json` so re-opens don't re-call GPT
- [x] `documents` — PDF generation (`/wizard/<slug>/generate/`) via WeasyPrint, federal-court formatting (Letter, Times 12pt, 1in margins, double-spaced body, numbered paragraphs, page footers, signature pinned to avoid orphaning)
- [x] `documents` — `caselaw_picker.py` auto-selects one foundational `CaseLaw` row per claim via `AMENDMENT_CATEGORY_MAP` (Glik for `1st`, Nieves for `1st_retaliation`, Graham for `4th_excessive_force`, Terry for `4th_seizure`, etc.). Adds Monell automatically when the document has a named government entity. Skips amendments with no curated case
- [x] `documents` — `caselaw_strategy` drives draft + PDF rendering: `inline` → one-sentence cite under each count; `appendix` → "Statement of Legal Authority" section after the prayer (Roman-numbered dynamically); `memorandum` → separate "Memorandum of Supporting Authority" page after the signature; `none` → omitted (default)
- [x] `documents` — Step 7 preview of the cases that will be cited so the user sees exactly what'll appear before clicking Generate
- [x] `documents` — Supporting Evidence section in the complaint (numbered paragraphs listing each item, type, source, deep-linked URL with timestamp). YouTube/Vimeo URLs deep-link to the key timestamp via `_build_play_url()` (YouTube `?t=Ns`, Vimeo `#t=Ns`, generic `#t=N`)
- [x] `documents` — admin-editable PDF watermark + footer (`PdfBranding` model). Diagonal red "DRAFT / NOT FOR FILING" stamp on every page of unpaid PDFs plus an italic footer-left line ("Draft preview — upgrade at www.file1983.com to download a clean copy."). Watermark text is a TextField so admins can put real newlines in. Toggling `payment_status='paid'` later flips the watermark off automatically
- [x] `documents` — end-to-end test suite (`documents/tests.py:WizardEndToEndTest`) — register → profile → wizard steps 1-7 → case law → draft → PDF, with mocked GPT calls. Runs in ~3 seconds
- [x] Step 7 "Generate Complaint" button now links to the draft page (placeholder removed)
- [x] Migrations through `0011_pdfbranding_watermark_textfield`
- [x] Dockerfile: `fonts-liberation` + `fonts-dejavu` for WeasyPrint

### Open
- [ ] Per-claim case law selection UI (Option B — let users curate which cases apply to which claims rather than auto-pick by amendment). Only worth building once we see whether users actually want curation; the auto-pick covers most auditor cases
- [ ] Stripe payment integration — gate `wizard_generate` view on `document.payment_status == 'paid'` once wired (the watermark already auto-disappears when payment_status='paid')
- [ ] Landing page CMS (`public_pages` is currently a stub)
- [ ] **Deploy to Render** — see "Next Step: Deploy" below
- [ ] Playwright/Selenium browser tests for JS interactions (Alpine cards, timestamp spinner, draft textareas)

---

## What's Built — Detail

### Wizard Flow (current)
1. User goes to `/documents/new/` → profile gate → Document + WizardSession + PlaintiffInfo created
2. Story page (`wizard_story`) — user types story, clicks Analyze
   - Alpine.js inline progress animation plays (7-step fake progress, 1.8s per step)
   - POST → `_gpt_test()` → calls `extract_story(session, dry_run=False)`
   - Full extraction printed to terminal (`docker compose logs -f web`)
   - Redirects to summary page
   - **bfcache fix**: a `pageshow` listener resets Alpine `analyzing=true` so clicking browser-back from summary doesn't show the spinner again. GPT only runs on POST; back navigation never re-calls it
3. Summary page (`wizard_extraction_summary`) — shows what GPT found vs missed (red/yellow/green banner), per-category status, Improve / Continue actions
4. Step 1 (`wizard_step1`) — federal jurisdiction only (auto-populate court via `CourtLookupService`, confirm checkbox, manual override)
5. Step 2 (`wizard_step2`) — incident details (date/time/address/city/state/county/location/activity/force/equipment); changing city/state clears court and bounces back to Step 1
6. Step 3 (`wizard_step3`) — defendants (Alpine cards, indexed POST `def_N_*`); government entity Monell section at bottom
7. Step 4 (`wizard_step4`) — constitutional claims (amendment + how_violated); plain-English guidance per claim; "Suggested from your story" badge on GPT-populated claims; `normalize_amendment()` at render time so stale DB values pre-select the dropdown
8. Step 5 (`wizard_step5`) — evidence & witnesses (Alpine multi-record); video/body_cam evidence shows the **Key Timestamp** input (input-group with `−`/`+` spinner buttons + free-typing text field that auto-converts periods to colons; on blur normalizes to `HH:MM:SS`)
9. Step 6 (`wizard_step6`) — damages, relief, prior complaints. **Use recommended** button one-clicks the six standard 1983 asks; frequency badges (Standard / Common / Specific cases) next to each relief item
10. Step 7 (`wizard_step7`) — final review with pencil-edit links. Shows Case Law Strategy card with the exact cases that will be cited (when strategy ≠ none). Evidence card shows Key Timestamp with a "Starts at HH:MM:SS" badge linking to the deep-linked video URL. **Clickable progress dots** at the top let the user jump back to any reached step
11. Case law strategy (`wizard_caselaw_strategy` at `/wizard/<slug>/caselaw/`) — 4-option chooser (none / inline / memorandum / appendix); saves to `Document.caselaw_strategy`
12. **Draft preview** (`wizard_draft` at `/wizard/<slug>/draft/`):
    - On first GET, calls `generate_factual_allegations(document)` → mocks/calls GPT → caches result in `Document.factual_allegations_json`. Subsequent GETs render from cache
    - Renders the full complaint in court format with the Factual Allegations section as auto-sizing textareas (other sections are read-only — they come from wizard data)
    - "Case No. ___ (Left blank — clerk assigns when filed)" hint visible on draft only
    - Action bar: **Save edits**, **Re-draft from story** (confirms first), **Generate PDF**
13. **PDF download** (`wizard_generate` at `/wizard/<slug>/generate/`):
    - Renders `templates/documents/pdf/complaint.html` through WeasyPrint
    - Diagonal red watermark + footer line on every page when `document.payment_status != 'paid'`
    - Inline `Content-Disposition` so it opens in browser PDF viewer; filename `<title>_<slug>.pdf`

### GPT Extraction (`documents/services/openai_service.py`)
- `extract_story(session, dry_run=False)` — calls GPT-4o, parses JSON, calls `_populate_models()`
- `_populate_models()` — writes all wizard models from `ai_analysis` JSON
  - Always resets `federal_district_court=''` and `court_confirmed=False` on re-analysis
  - Deletes and recreates: TimelineEntry, Defendant, ConstitutionalClaim, Evidence, Witness
  - Update-or-create: PlaintiffInfo, IncidentOverview, GovernmentEntity, Damages, PriorComplaints, ReliefSought
  - Updates Document.title if GPT provided one
  - ConstitutionalClaim amendments run through `normalize_amendment()` + deduped
- `normalize_amendment(value)` and `normalize_state(value)` — public helpers used both during extraction and at render time to self-heal stale rows

### Complaint Drafter (`documents/services/complaint_drafter.py`)
- `generate_factual_allegations(document)` — turns `story_text` + structured wizard data into a numbered list of first-person paragraphs
- Hard-rule system prompt: first person, past tense, plain English, no Latin, no Bluebook, no legal characterization, no citations, defendants' names verbatim, never invent facts beyond the story
- Temperature 0.2, JSON-only output
- Returns `(paragraphs_list, error_str)` — caller saves to `Document.factual_allegations_json`

### Case Law Picker (`documents/services/caselaw_picker.py`)
- `AMENDMENT_CATEGORY_MAP` — maps each `ConstitutionalClaim.amendment` key → `CaseLaw.category`
- `select_supporting_cases(document)` — returns a deduped list of `{'claim', 'case', 'kind'}` dicts. Picks the top-ordered case per category, plus Monell when there's a named government entity
- Skips amendments without a curated case (better than citing something unrelated)

### Court Lookup (`documents/services/court_lookup_service.py`)
- `CourtLookupService.lookup_court_by_location(city, state)`
- Three-tier: static city map → state-level fallback → GPT-4o fallback
- State files in `documents/services/court_data/states/` (54 files, all states + DC + territories)

### PDF Branding (`PdfBranding` model)
- Singleton-style admin-editable copy used on draft (unpaid) PDFs
- Fields: `watermark_text` (TextField, supports newlines), `footer_text`, `website_url`, `is_active`
- Defaults seeded by migration `0010`: "DRAFT\nNOT FOR FILING" + "Draft preview — upgrade at www.file1983.com to download a clean copy." + "www.file1983.com"
- Toggle multiple rows via `is_active` to A/B copy without losing previous versions

### Models — Key Notes
- `Damages.lost_wages` and `property_damage_amount` are **TextField** (not Decimal) — GPT returns strings like "Missed a work shift"
- `WizardSession.ai_extraction_succeeded` controls which state the story page renders
- All wizard model fields are `blank=True` / `null=True` — partial extraction never breaks anything
- Document ownership enforced on every view: `get_object_or_404(Document, slug=slug, user=request.user)`
- `Document.caselaw_strategy` — CharField with choices `none / inline / memorandum / appendix`, default `none`
- `Document.factual_allegations_json` — JSONField, shape `{"paragraphs": ["...", "..."]}`. Set when user first opens the draft page; updated when they edit; replaced when they click Re-draft
- `Evidence.key_timestamp` — CharField storing `"HH:MM:SS"` format; `_normalize_timestamp()` and the JS layer both accept periods or colons
- `IncidentOverview.state` is stored as a 2-letter code (e.g. `FL`, not `Florida`). `normalize_state()` enforces this at extraction time; `_heal_state_code()` self-heals on render
- Section roman numerals in the PDF are computed dynamically by `_build_complaint_context()` so they shift correctly when sections are present or absent

### Migration History
- `0001_initial` — all initial models
- `0002_examplestory` — ExampleStory model
- `0003_damages_wages_to_textfield` — `Damages.lost_wages` + `property_damage_amount` AutoField → TextField
- `0004_expand_location_type_choices` — added 27 grouped location types
- `0005_caselaw` — CaseLaw model
- `0006_alter_caselaw_id` — auto: AutoField → BigAutoField on CaseLaw.id
- `0007_document_caselaw_strategy` — adds `Document.caselaw_strategy`
- `0008_document_factual_allegations_json` — adds the JSON cache field for the AI-drafted paragraphs
- `0009_evidence_key_timestamp` — adds `Evidence.key_timestamp` (CharField max_length=20)
- `0010_pdfbranding` — creates `PdfBranding` model and seeds the `default` row
- `0011_pdfbranding_watermark_textfield` — `watermark_text` CharField → TextField, default updated to two-line "DRAFT\nNOT FOR FILING"

### `ai_analysis` JSON shape (what GPT returns, stored in `WizardSession.ai_analysis`)
```json
{
  "document": { "title": "", "jury_trial_demand": true },
  "plaintiff": { "full_name": "", "address": "", "city": "", "state": "", "zip_code": "", "phone": "", "email": "", "filing_pro_se": true },
  "incident": { "incident_date": "YYYY-MM-DD", "incident_time": "HH:MM", "address": "", "city": "", "state": "", "county": "", "location_description": "", "location_type": "", "is_public_forum": null, "plaintiff_activity": "", "force_used": null, "equipment_seized_or_damaged": null },
  "timeline": [ { "order": 1, "time_approximate": "", "actor": "", "action_description": "" } ],
  "defendants": [ { "full_name": "", "badge_number": "", "rank_title": "", "agency_name": "", "capacity_sued": "both", "acting_under_color_of_law": true, "is_supervisor": false } ],
  "government_entity": { "entity_name": "", "entity_address": "", "policy_or_custom_description": "" },
  "constitutional_claims": [ { "amendment": "", "how_violated": "" } ],
  "evidence": [ { "evidence_type": "", "description": "", "date_and_time": "", "recorded_by": "", "public_url": "", "key_timestamp": "", "defendant_aware_of_recording": null } ],
  "witnesses": [ { "full_name": "", "contact_info": "", "relationship_to_plaintiff": "", "what_they_witnessed": "", "has_video": null, "willing_to_testify": null } ],
  "damages": { "physical_injury_description": "", "emotional_distress_description": "", "lost_wages": null, "property_damage_amount": null, "punitive_basis": "" },
  "relief": { "compensatory_damages": false, "compensatory_amount": null, "punitive_damages": false, "declaratory_judgment": false, "injunctive_relief": false, "attorney_fees": false, "costs_of_suit": false, "other_relief": "" },
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

Load: `docker compose exec web python manage.py loaddata example_stories`
Dropdown shows only for `is_staff` users or when `DEBUG=True`

### Case Law Library (`documents/fixtures/foundational_case_law.json`)
- 15 foundational real federal cases covering the core of 1983 litigation:
  - 1st Am. recording: Glik, Turner, Fields, Alvarez, Smith v. Cumming
  - 1st Am. retaliation: Nieves, Hartman
  - 4th Am. excessive force: Graham v. Connor, Tennessee v. Garner
  - 4th Am. seizure: Terry, Bostick
  - Qualified immunity: Harlow, Pearson
  - Monell / §1983 general: Monell, Monroe v. Pape
- Auto-picked into draft + PDF via `caselaw_picker.py` based on `Document.caselaw_strategy`
- Load: `docker compose exec web python manage.py loaddata foundational_case_law`

### Pro se voice rule
Per design discussion: keep factual allegations in **plain first person** ("On March 3, 2024, I was filming…"), not third-person legalese. Reserve formal legal phrasing for the count headings and the prayer for relief — those are unavoidably formal. **Do not** use Bluebook parentheticals, signal abbreviations, or Latin beyond the few unavoidable terms (e.g. "pro se" itself). Goal: a complaint that reads as competent but unmistakably written by the plaintiff. This is enforced via the `complaint_drafter.py` system prompt.

---

## Test Suite (`documents/tests.py`)

End-to-end happy-path test that walks one user from registration through to a downloaded PDF, with GPT calls mocked at the service boundary.

```bash
docker compose exec web python manage.py test documents.tests.WizardEndToEndTest -v 2
```

Runs in ~3 seconds. Asserts:
- Registration + login + profile completion
- Document creation, story extraction populates models
- All seven wizard steps advance correctly
- Step 5 timestamp normalization (`"1.30.45"` → `"01:30:45"`)
- Case-law auto-selection (Nieves, Terry, Monell with gov entity)
- Draft generation + edit-and-save round trip
- Real WeasyPrint PDF response (`%PDF` blob > 1KB)

What it **doesn't** cover: Alpine.js interactions (Playwright/Selenium later), real GPT quality (manual sanity), Stripe (not wired).

---

## Next Step: Deploy to Render

The app is feature-complete for an MVP launch except payment. Goal: get it live at `https://file1983.com` with `auditfile1983.com` redirecting in.

### Render setup outline

1. **Create a Render PostgreSQL database** (the `Starter` plan is fine to start). Copy the internal connection string.
2. **Create a Render Web Service**, point it at the GitHub repo's `master` branch.
   - Runtime: Docker (uses the existing `Dockerfile`)
   - Health check path: `/`
   - Region: same as the database (US-Ohio or similar) for free internal networking
3. **Environment variables** on the web service — copy values from local `.env`:
   - `SECRET_KEY` (generate fresh, do **not** reuse the dev one)
   - `DEBUG=0`
   - `ALLOWED_HOSTS=file1983.com,www.file1983.com,auditfile1983.com,www.auditfile1983.com,<your-app>.onrender.com`
   - `DATABASE_URL` — from the Render Postgres internal connection string
   - `OPENAI_API_KEY`
   - `EMAIL_HOST=mail.privateemail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`
   - `EMAIL_HOST_USER=rights@file1983.com`, `EMAIL_HOST_PASSWORD=<rotated value>`, `DEFAULT_FROM_EMAIL=rights@file1983.com`
   - `ADMIN_URL=<something-non-obvious>/`
   - Stripe keys can stay blank until ready
4. **Static files** — `whitenoise` is already in middleware and `STATICFILES_STORAGE` is `CompressedManifestStaticFilesStorage`. Render needs `collectstatic` to run on each deploy. Add a build step in render.yaml (or the dashboard's Build Command):
   ```
   pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput
   ```
5. **Custom domains** in Render dashboard:
   - Add `file1983.com` and `www.file1983.com` to the web service. Render shows the DNS records to set at Namecheap (typically an `ALIAS`/`ANAME` for the apex and a `CNAME` for `www`)
   - Add `auditfile1983.com` and `www.auditfile1983.com` to the **same** web service. Render auto-issues a TLS cert for each
   - **Redirect logic** — point `auditfile1983.com` to `file1983.com` either via:
     - **Namecheap URL Redirect Record** (simplest — set at the registrar, no app code needed). Source `auditfile1983.com` → `https://file1983.com` (permanent 301). Repeat for `www.`
     - OR keep both pointing at the Render service and add Django middleware that 301-redirects any `auditfile1983.com` host to `file1983.com`. Simpler to keep DNS-level, recommended
6. **Email DNS records** — make sure SPF/DKIM/DMARC for `file1983.com` are set per Namecheap Private Email instructions, otherwise password-reset emails will land in spam
7. **First deploy checklist after the service is up**:
   - SSH-equivalent: open the Render Shell and run:
     ```
     python manage.py migrate
     python manage.py loaddata foundational_case_law
     # don't load example_stories in prod — they're staff-only test data
     python manage.py createsuperuser
     ```
   - Verify the watermark renders on a test PDF (open `/manage-dev/documents/pdfbranding/`, confirm the `default` row exists)
   - Send a test password-reset email to confirm SMTP works

### Deploy gotchas to watch for

- **`CompressedManifestStaticFilesStorage`** requires `collectstatic` to run before any template using `{% static %}` will render. The build command above handles it. The test suite overrides this to plain `StaticFilesStorage` to avoid the dependency.
- **WeasyPrint system libs** are already in the Dockerfile (`libpango`, `libpangoft2`, `libharfbuzz`, `fonts-liberation`, `fonts-dejavu`). The Render Docker build picks these up automatically
- **`SECURE_PROXY_SSL_HEADER`** — Render terminates TLS at its load balancer. Make sure `settings.py` reads `HTTP_X_FORWARDED_PROTO` so Django knows requests are HTTPS:
  ```python
  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
  ```
  Add this if it's not already set
- **`CSRF_TRUSTED_ORIGINS`** — Django 4.0+ requires this for any non-localhost host. Set:
  ```python
  CSRF_TRUSTED_ORIGINS = [
      'https://file1983.com', 'https://www.file1983.com',
      'https://auditfile1983.com', 'https://www.auditfile1983.com',
  ]
  ```

### After-deploy tasks
- Verify `/documents/<slug>/wizard/draft/` runs the GPT call (check OpenAI dashboard for usage)
- Verify a full wizard flow + PDF download against the live URL
- Set up Render's free uptime monitoring on `/`

---

## Design Rules
- Do not redesign — color palette, navbar, footer, fonts are fixed
- Master theme: `static/css/app-theme.css`
- Headings use Playfair Display (`font-family:'Playfair Display',serif`)
- Alpine.js for all frontend interactivity (already loaded in base.html)
- Bootstrap 5.3 classes only — no custom CSS unless absolutely necessary
- Flash messages: use Django `messages` framework (already wired in base.html)
- Keep wizard steps focused — one decision per page, no overwhelming forms
- PDF complaint formatting follows federal court conventions: Times 12pt, 1in margins, double-spaced body, numbered paragraphs via CSS counters
