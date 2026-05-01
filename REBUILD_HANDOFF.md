# 1983 Law — Project Handoff

## The App
A Django web app that guides users through building a **Section 1983 civil rights complaint**
against government officials. Target users: First Amendment auditors, citizens documenting
police misconduct, unlawful arrest, excessive force, retaliation for recording in public.

Flow: User tells their story → AI extracts structured data → wizard lets user review/edit
each section → final review → PDF download → Stripe payment to unlock.

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
git merge claude/<short-description>
git push origin master
```

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
/documents/<slug>/wizard/step3/            → Step 3: defendants (add/edit/delete) + government entity
/documents/<slug>/wizard/step4/            → Step 4: constitutional claims (add/edit/delete)
/documents/<slug>/wizard/step5/            → Step 5: evidence & witnesses (multi-record)
/documents/<slug>/wizard/step6/            → Step 6: damages, relief, prior complaints
/documents/<slug>/wizard/step7/            → Step 7: final review (read-only with edit links)
/documents/<slug>/wizard/caselaw/          → Case law strategy choice (post-review, optional)
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
- [x] `documents` — 27 grouped location types (police station lobby, courthouse, DMV, post office, etc.) with optgroup dropdown
- [x] `documents` — Step 3: defendants (Alpine.js dynamic add/edit/delete cards, government entity Monell section)
- [x] `documents` — Step 4: constitutional claims (add/edit/delete, duplicate-amendment protection)
- [x] `documents` — Step 4 guidance: plain-English amendment descriptions + examples per claim, attorney-consultation disclaimer, "Suggested from your story" badge on GPT-populated claims
- [x] `documents` — amendment normalization (`normalize_amendment()`) so GPT loose values like "First" map to canonical keys like `1st_retaliation`; applied in extraction and Step 4 render
- [x] `documents` — CaseLaw model + admin + 15 foundational cases fixture (wired in later — no UI yet)
- [x] `documents` — Step 5: evidence & witnesses (Alpine.js multi-record, two sections on one page)
- [x] `documents` — Step 6: damages, relief sought, prior complaints (single-form, all OneToOne)
- [x] `documents` — Step 7: final review (read-only summary of every section with pencil-edit links back to each step)
- [x] `documents` — case law strategy chooser (`/wizard/<slug>/caselaw/`) — 4-option page (none / inline / memorandum / appendix) with pro-se / Twombly-Iqbal / Haines explanation; saved on `Document.caselaw_strategy`
- [x] `documents` — state code normalization (`normalize_state()` in openai_service) so GPT "Florida" → "FL" matches the Step 2 dropdown; self-heals existing rows on Step 1/2 render
- [x] `documents` — complaint draft page (`/wizard/<slug>/draft/`) with AI-drafted, user-editable factual allegations + full preview of the complaint (caption, jurisdiction, parties, counts, damages, prayer, signature)
- [x] `documents` — `complaint_drafter.py` GPT service that turns `story_text` + structured wizard data into numbered first-person factual allegations. Hard-rule prompt: no new facts, no legal characterization, no citations, plain English. Returns `{"paragraphs": [...]}`. Cached on `Document.factual_allegations_json` so re-opens don't re-call GPT.
- [x] `documents` — PDF generation (`/wizard/<slug>/generate/`) via WeasyPrint, federal-court formatting (Times 12pt, 1in margins, double-spaced, numbered paragraphs)
- [x] Step 7 "Generate Complaint" button now links to the draft page (placeholder removed)
- [x] Migration `0008_document_factual_allegations_json` adds the JSON cache field
- [x] Dockerfile: added `fonts-liberation` + `fonts-dejavu` for WeasyPrint
- [ ] Per-claim case law selection UI (only relevant if user picked `inline` / `memorandum` / `appendix` strategy — `none` skips this)
- [ ] Wire `caselaw_strategy` into the PDF — currently the draft + PDF templates ignore it (renders the same complaint regardless of strategy). Once per-claim selection UI exists, plumb selected `CaseLaw` rows into the templates: inline → one short cite per count, memorandum → separate PDF, appendix → "STATEMENT OF LEGAL AUTHORITY" section after prayer.
- [ ] Stripe payment integration — gate `wizard_generate` view on `document.payment_status == 'paid'` once wired
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
   - On save: advances `current_step` to 3, redirects to Step 3
   - Reusable progress indicator: `templates/documents/_wizard_progress.html`
6. Step 3 (`wizard_step3`) — defendants
   - Alpine.js dynamic defendant cards: add, edit, delete, expand/collapse
   - Each card: full_name, badge_number, rank_title, agency_name, capacity_sued, acting_under_color_of_law, is_supervisor
   - Defendants serialized as indexed POST fields (`def_0_full_name`, etc.)
   - View updates existing defendants by PK, creates new ones, deletes removed ones
   - Government Entity (Monell claim) section at bottom: entity_name, entity_address, policy_or_custom_description
   - On save: advances `current_step` to 4, redirects to Step 4
7. Step 4 (`wizard_step4`) — constitutional claims
   - Alpine.js dynamic claim cards: amendment dropdown + how_violated textarea
   - **Plain-English guidance** per claim via `AMENDMENT_INFO` dict in views.py — each amendment has a description + common examples; toggled via "What does this protect?" link per card; auto-expands when user picks a new amendment
   - **Legal disclaimer banner** at top: warns users civil rights law is complex and recommends attorney consultation
   - **"Suggested from your story"** blue badge on pre-populated claims (has PK + how_violated)
   - **Amendment normalization**: `normalize_amendment()` in `openai_service.py` maps loose AI values ("First", "Fourth Amendment — Retaliation", etc.) to canonical keys. Applied at render time so stale DB values still pre-select the dropdown; canonical value saved back on next form submission
   - Duplicate amendment detection (client-side warning + server-side skip) since `(document, amendment)` is unique_together
   - Indexed POST fields (`claim_0_amendment`, etc.)
   - On save: advances `current_step` to 5, redirects to Step 5
8. Step 5 (`wizard_step5`) — evidence & witnesses
   - Two sections on one page, both Alpine.js multi-record cards (same pattern as Step 3)
   - **Evidence cards**: type dropdown (video / photo / police_report / body_cam / foia_request / citation / medical_record / physical / document / other), description, date_and_time (free text), recorded_by, public_url, defendant_aware_of_recording (tristate select)
   - **Witness cards**: full_name, contact_info, relationship_to_plaintiff, what_they_witnessed, has_video (tristate select), willing_to_testify (tristate select)
   - Both sections start at zero cards (optional — informational alert if empty)
   - Indexed POST fields (`ev_N_*`, `wit_N_*`); update-by-pk for existing, create for new, delete removed
   - Empty rows skipped server-side (evidence: must have description or public_url; witness: must have full_name or what_they_witnessed)
   - On save: advances `current_step` to 6, redirects to Step 6
9. Step 6 (`wizard_step6`) — damages, relief, prior complaints
   - Single-form page (no Alpine cards) since all three models — `Damages`, `ReliefSought`, `PriorComplaints` — are OneToOne with Document
   - **Damages**: physical injury, emotional distress, lost wages, property damage, punitive basis (all text)
   - **Relief Sought**: 6 checkbox cards with plain-English explanations — compensatory (with optional `$` amount that reveals when checked), punitive, declaratory, injunctive, attorney's fees (cites § 1988), costs of suit, plus an "other relief" catch-all
   - **Prior Complaints**: `filed_complaints` checkbox; description + outcomes textareas reveal when checked (Alpine `x-show`)
   - On save: advances `current_step` to 7, redirects to Step 7
10. Step 7 (`wizard_step7`) — final review
    - Read-only summary of every section with pencil-edit links back to each step
    - Cards: Document, Plaintiff, Jurisdiction, Incident, Defendants, Government Entity (Monell, only shown if `entity_name`), Constitutional Claims, Evidence, Witnesses, Damages, Relief Sought, Prior Complaints (only shown if `filed_complaints=True`), Case Law Strategy
    - Empty fields render in muted italic so missing data is visible
    - Plaintiff card edit link goes to `accounts:profile` (since plaintiff data syncs from the user profile)
    - Bottom action: disabled "Generate Complaint — Coming next" button (placeholder for PDF generation)
    - Includes `_heal_state_code()` call so any stale `incident.state` value (e.g. "Florida") gets rewritten to the 2-letter code on render
11. Case law strategy (`wizard_caselaw_strategy` at `/wizard/<slug>/caselaw/`) — post-review, optional
    - Reachable from the Case Law Strategy review card on Step 7 (pencil link)
    - 4 click-to-select cards: **none** (default — plead facts only, most pro se), **inline** (one controlling case per claim woven in), **memorandum** (separate companion document), **appendix** (Statement of Legal Authority attached)
    - Top of page explains the *Twombly/Iqbal* fact-pleading rule, *Haines v. Kerner* pro se leniency, and the ghostwriting concern
    - Each card shows pros/cons + risk/credibility pills (Most pro se / Some risk / Balanced / etc.)
    - Saves to `Document.caselaw_strategy` (CharField with 4 choices, default `none`); migration `0007_document_caselaw_strategy`
    - On save: redirects back to Step 7 with a flash message confirming the choice

### GPT Extraction (`documents/services/openai_service.py`)
- `extract_story(session, dry_run=False)` — calls GPT-4o, parses JSON, calls `_populate_models()`
- `_populate_models()` — writes all wizard models from `ai_analysis` JSON:
  - Always resets `federal_district_court=''` and `court_confirmed=False` on re-analysis
  - Deletes and recreates: TimelineEntry, Defendant, ConstitutionalClaim, Evidence, Witness
  - Update-or-create: PlaintiffInfo, IncidentOverview, GovernmentEntity, Damages, PriorComplaints, ReliefSought
  - Updates Document.title if GPT provided one
  - ConstitutionalClaim amendments run through `normalize_amendment()` + deduped to respect `unique_together(document, amendment)`
- `normalize_amendment(value)` — public helper exported from this module. Maps loose amendment values to canonical `ConstitutionalClaim.AMENDMENT_CHOICES` keys. Used by Step 4 view at render time too
- Prompt tells GPT the exact allowed keys with plain-English hints (e.g. "use `1st_retaliation` for arrests after filming police — most auditor cases fall here") and instructs it to include multiple claims when appropriate (e.g. `1st_retaliation` + `4th_seizure` for a filming arrest)

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
- `Document.caselaw_strategy` — CharField with choices `none / inline / memorandum / appendix`, default `none`. Read this when generating the PDF to decide whether (and how) to include `CaseLaw` rows.
- `IncidentOverview.state` is stored as a 2-letter code (e.g. `FL`, not `Florida`). `normalize_state()` in `openai_service.py` enforces this at extraction time; `_heal_state_code()` in `views.py` self-heals any old rows on Step 1, 2, or 7 render.

### Migration History
- `0001_initial` — all initial models
- `0002_examplestory` — ExampleStory model
- `0003_damages_wages_to_textfield` — `Damages.lost_wages` + `property_damage_amount` AutoField → TextField
- `0004_expand_location_type_choices` — added 27 grouped location types
- `0005_caselaw` — CaseLaw model
- `0006_alter_caselaw_id` — auto: AutoField → BigAutoField on CaseLaw.id (DEFAULT_AUTO_FIELD alignment)
- `0007_document_caselaw_strategy` — adds `Document.caselaw_strategy`

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

### Case Law Library (`documents/fixtures/foundational_case_law.json`)
- 15 foundational real federal cases covering the core of 1983 litigation:
  - 1st Am. recording: Glik, Turner, Fields, Alvarez, Smith v. Cumming
  - 1st Am. retaliation: Nieves, Hartman
  - 4th Am. excessive force: Graham v. Connor, Tennessee v. Garner
  - 4th Am. seizure: Terry, Bostick
  - Qualified immunity: Harlow, Pearson
  - Monell / §1983 general: Monell, Monroe v. Pape
- Admin-managed via `CaseLaw` model. Each case has plain-English holding summary,
  why-it-matters for auditors, optional key quote, and jurisdiction notes
- Load into DB: `docker compose exec web python manage.py loaddata foundational_case_law`
- **Not yet wired to UI.** Deferred feature: Step 4 will let users browse these per-claim
  and opt-in to include specific cases as supporting authority in their complaint.
  Design note: only curated cases — never AI-generated citations (hallucination risk)

---

## Next Step: PDF Generation

The wizard is **complete end-to-end** — story → extraction → 7 review/edit steps → final review → optional case law strategy choice. The only thing standing between a user and a filed complaint is rendering it as a PDF.

**Replace** the disabled "Generate Complaint — Coming next" button at the bottom of `templates/documents/wizard_step7.html`.

**URL to add:** `GET /documents/<slug>/wizard/generate/` — calls WeasyPrint, streams a PDF response.

### What the PDF needs to render
A federal §1983 complaint in the standard form:
1. **Caption** — court (`incident.federal_district_court`), parties (plaintiff vs. each defendant), case no. blank, "COMPLAINT FOR VIOLATION OF CIVIL RIGHTS"
2. **Jurisdiction & Venue** — federal question (28 U.S.C. § 1331), § 1983 (42 U.S.C. § 1983), venue facts from `incident`
3. **Parties** — Plaintiff section + one section per Defendant + Government Entity (Monell) if `gov_entity.entity_name`
4. **Factual Allegations** — narrative built from `incident.plaintiff_activity` + ordered `TimelineEntry` rows + force/equipment facts
5. **Constitutional Claims** — one count per `ConstitutionalClaim`. Use `c.get_amendment_display()` as count title and `c.how_violated` as the substantive paragraphs
6. **Evidence & Witnesses** — short prose listing of each, often combined into the factual allegations or a separate "Supporting Evidence" section
7. **Damages** — paragraphs from `Damages` fields
8. **Prayer for Relief** — one bullet per checked `ReliefSought` field + `other_relief`
9. **Jury Demand** — one line if `document.jury_trial_demand`
10. **Signature block** — plaintiff name, address, phone, email, "Pro Se" if `plaintiff.filing_pro_se`
11. **Case law** — depends on `document.caselaw_strategy`:
    - `none` — omit entirely
    - `inline` — add a sentence per claim like "The right to record police was clearly established in *Glik v. Cunniffe*, 655 F.3d 78 (1st Cir. 2011)" (case selection UI not yet built — for now hardcode one controlling case per amendment from the `CaseLaw` library)
    - `memorandum` — generate as a SEPARATE PDF (or PDF appendix), not in the complaint body
    - `appendix` — append a "STATEMENT OF LEGAL AUTHORITY" section after the prayer for relief

### Pro se voice rule
Per design discussion 2026-04-29: keep factual allegations in **plain first person** ("On March 3, 2024, I was filming…"), not third-person legalese ("Plaintiff was engaged in protected First Amendment activity when…"). Reserve formal legal phrasing for the count headings and the prayer for relief — those are unavoidably formal. **Do not** use Bluebook parentheticals, signal abbreviations, or Latin beyond the few unavoidable terms (e.g. "pro se" itself). Goal: a complaint that reads as competent but unmistakably written by the plaintiff.

### Files to add
- `documents/services/pdf_service.py` — main entry point: `render_complaint_pdf(document)` returns bytes
- `templates/documents/pdf/complaint.html` — WeasyPrint template (HTML/CSS, federal court style: 12pt Times, 1in margins, double-spaced body, numbered paragraphs)
- `templates/documents/pdf/_complaint_caption.html`, `_complaint_count.html`, etc. — partials per section
- `documents/views.py:wizard_generate` — view that builds context, calls service, returns `HttpResponse(content_type='application/pdf')`
- New URL `wizard_generate` at `/documents/<slug>/wizard/generate/`

### Stack notes
- **WeasyPrint** is already in the planned stack — needs `apt-get install` of system libs (libpango, libcairo, etc.) in the Dockerfile if not already present. Check `Dockerfile` first.
- Numbered paragraphs are a federal court convention — use a CSS counter (`counter-reset` / `counter-increment`) on the body
- Keep the template in pure HTML/CSS; do not require JavaScript to render

### Stripe gate
PDF generation is the natural place to insert the **payment gate**. For now, allow free PDF download. When Stripe is wired, gate the `wizard_generate` view on `document.payment_status == 'paid'`. The wizard itself stays free; payment only unlocks the final document.

---

## Design Rules
- Do not redesign — color palette, navbar, footer, fonts are fixed
- Master theme: `static/css/app-theme.css`
- Headings use Playfair Display (`font-family:'Playfair Display',serif`)
- Alpine.js for all frontend interactivity (already loaded in base.html)
- Bootstrap 5.3 classes only — no custom CSS unless absolutely necessary
- Flash messages: use Django `messages` framework (already wired in base.html)
- Keep wizard steps focused — one decision per page, no overwhelming forms
