# 1983 Law — Project Handoff

## The App
A Django web app that guides users through building a **Section 1983 civil rights complaint**
against government officials. Target users: First Amendment auditors, citizens documenting
police misconduct, unlawful arrest, excessive force, retaliation for recording in public.

Flow: User tells their story → AI extracts structured data → wizard lets user review/edit
each section → final review → AI drafts factual allegations → user reviews/edits draft → PDF download → Stripe payment to remove draft watermark.

---

## Where we are right now (read this first)

**Status:** MVP is feature-complete and live on Render at `file1983.com` (Stripe in sandbox/test mode). Recent test users have completed full purchase flows successfully.

**What works end-to-end today:**
- Story → wizard → AI draft → preview PDF → pay $149 (or $99 with promo code) → webhook flips status → clean PDF download → finalize lock
- Promo codes track referrer attribution; admin shows per-code revenue and the partner cut
- AI quota limits prevent runaway OpenAI spend on a single document
- Free-doc cap stops users from creating unlimited drafts
- One-step undo restores the previous draft after a regenerate
- Stale-draft block forces users to regenerate before viewing an outdated draft

**Latest commits (most recent on top), all on `master` and deployed:**
- `1d20253` — Dark-mode contrast boost for outline buttons across the wizard
- `ecdbfe4` — Stale-draft view block + one-step undo of regenerate (migration 0017)
- `6e7179d` — AI quota per document + Finalize & Lock (Stripe Phase 4 + abuse limits, migration 0016)
- `ac406b7` — Admin reporting: promo-code revenue, partner cut, CSV export (migration 0015)
- `820fd5d` — Stripe webhook JSON-payload parse (works around StripeObject .get() removal in v10+)
- `357bbc5` — Stripe webhook bulletproof exception handling
- `fa139f2` — Stripe webhook surfaces handler exceptions as JSON (debugging aid)
- `77d41f1` — Stripe Phase 3: webhook + attachment download (migration 0014)
- `95070c5` — Stripe Phase 2: Checkout Session + promo validation + Pay button

**Settings worth knowing about (all in `config/settings.py`):**
- `PRICE_FULL_CENTS=14900` / `PRICE_DISCOUNTED_CENTS=9900` — list and promo prices
- `PARTNER_CUT_PERCENT=20` — referrer earns $19.80 on each $99 sale
- `AI_QUOTA_FREE=3` / `AI_QUOTA_PAID=150` — per-document AI call limits
- `FREE_DOCS_PER_USER=2` — max draft documents in flight per user

**What the next Claude should know about user preferences:**
- User wants step-by-step instructions, not autonomous large changes
- User can't always copy text outside of code blocks — always wrap commands, URLs, codes in triple backticks
- User is on Windows / PowerShell; chained commands need newlines, not `&&`
- User does NOT want to use terminal heavily — prefer admin UI and clickable URLs
- User tests on production Render with a few test accounts (no local Docker setup)
- Workflow: develop on `claude/<short-description>` branch → push → user merges to master locally → Render auto-deploys

**Likely next features (user's open roadmap, prioritized):**
1. Self-serve partner dashboard (`/partner/`) — referrers log in to see their own sales/earnings/payout history
2. Landing page CMS (`public_pages` is currently a stub)
3. Optional polish: per-claim case-law selection UI, Playwright/Selenium browser tests, more admin niceties

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
- **Payments:** Stripe (live on Render in test/sandbox mode; switch to live keys when ready to take real payments)
- **PDF:** WeasyPrint (wired — Letter, 1in margins, Times 12pt, double-spaced, page footers)
- **Auth:** Custom User model, email-based (no username); DRF + JWT exposed at `/api/v1/token/` (not currently used by the web UI)
- **Deploy:** Render (live at `file1983.com`, auto-deploys from `master`)

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
STRIPE_SECRET_KEY=               ← sk_test_... (sandbox) or sk_live_...
STRIPE_PUBLISHABLE_KEY=          ← pk_test_... or pk_live_...
STRIPE_WEBHOOK_SECRET=           ← whsec_... from Stripe Dashboard webhook destination
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
/documents/<slug>/wizard/                   → story input page (with Dictate voice button)
/documents/<slug>/wizard/summary/           → post-extraction summary (per-item "Add details" + "something else" addendum picker)
/documents/<slug>/wizard/addendum/          → POST: per-category story addendum (voice-friendly), non-destructive merge into wizard models
/documents/<slug>/wizard/step1/             → Step 1: federal jurisdiction / court confirmation
/documents/<slug>/wizard/step2/             → Step 2: incident details (date, location, activity, force)
/documents/<slug>/wizard/step3/             → Step 3: defendants (add/edit/delete) + government entity
/documents/<slug>/wizard/step4/             → Step 4: constitutional claims (add/edit/delete)
/documents/<slug>/wizard/step5/             → Step 5: evidence & witnesses (multi-record, video timestamps)
/documents/<slug>/wizard/step6/             → Step 6: damages, relief, prior complaints
/documents/<slug>/wizard/step7/             → Step 7: final review (read-only with edit links)
/documents/<slug>/wizard/caselaw/           → Case law strategy choice (post-review, optional)
/documents/<slug>/wizard/draft/             → AI-drafted factual allegations + full complaint preview, editable. Stale drafts redirect to Step 7
/documents/<slug>/wizard/draft/undo/        → POST: restore previous_factual_allegations snapshot (single-step undo of regenerate)
/documents/<slug>/wizard/generate/          → WeasyPrint PDF (watermarked unless paid). ?download=1 forces save dialog; ?finalize=1 (paid only) locks the doc to 'finalized' before serving
/documents/<slug>/pay/                      → Pay $149 (or $99 with promo code) — creates Stripe Checkout Session
/documents/<slug>/pay/validate-promo/       → AJAX: GET ?code=XYZ → live promo validation for the pay page
/documents/<slug>/pay/success/              → Stripe success_url; offers clean PDF download
/documents/<slug>/pay/cancel/               → Stripe cancel_url; flashes message + redirects to draft
/stripe/webhook/                            → Stripe webhook endpoint (csrf_exempt, signature-verified). Handles checkout.session.completed
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
- [x] Dockerfile: `fonts-liberation` + `fonts-dejavu` for WeasyPrint
- [x] **Render deploy prep** (commit `0d4212e`) — `docker-entrypoint.sh` runs migrate + collectstatic + gunicorn on `$PORT`; `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, and TLS-aware secure-cookie/SSL-redirect settings all wired in `config/settings.py` for `DEBUG=0`
- [x] **Voice dictation** (commit `f157c3f`) — `withVoice('prop')` Alpine helper in `base.html` mixes Web Speech recognition into any component. Wired into the main story textarea + the addendum modal. Hidden gracefully on unsupported browsers
- [x] **Per-category story addendums** (commit `f157c3f`) — `documents/services/addendum_service.py` (~700 lines): user can add details after extraction without re-running the full GPT pass. Snapshot of one category's current model state + new addendum text → GPT-4o → non-destructive merge. 9 categories (incident, defendants, claims, evidence, witnesses, damages, plaintiff, relief, prior_complaints). Existing rows are never deleted; list models match by key (defendant by name, claim by amendment, evidence by URL or type+desc); audit trail in `WizardSession.story_addendums` JSONField. Summary page has per-item "Add details" buttons + a "something else" picker; modal scoped to category with placeholder + voice button. New view: `wizard_addendum`. 6 tests in `StoryAddendumTest`
- [x] **Step 2 datetime UX** (commits `ef4ec30`, `e06a4cf`) — quick-chip buttons (Today/Yesterday/Last week, Now/Morning/Afternoon/Evening/Night) and live human-readable preview underneath. Click the date input → Flatpickr popup calendar (`maxDate=today`); click the time input → spinner picker with up/down arrows on hours, minute increments of 5, and AM/PM. Native picker still works underneath. Dark-mode CSS overrides for the popup match the app theme. Loaded from CDN
- [x] **Stale draft detection** (commit `a416383`) — `Document.factual_allegations_drafted_at` timestamp set whenever the draft is regenerated or saved. `_is_draft_stale(doc, session)` returns True when `wizard_session.updated_at > factual_allegations_drafted_at`. Yellow banner on the draft page with inline "Re-draft now" button. Migration `0013`
- [x] **Drafter prompt prefers structured data** (commit `800c1d4`) — `complaint_drafter.py` system prompt now explicit that structured wizard data (date/time/address/names/badges) reflects the user's most recent edits and wins on conflict; the story is the source of truth only for the sequence of events and what was said. Times rendered in 12-hour clock with am/pm
- [x] **Step 7 surfaces the Regenerate button** (commit `ddd7eaa`) — three states on the action area: no draft → "Generate Complaint"; draft exists & fresh → "Open Draft" primary + small "Regenerate" secondary; draft exists & stale → yellow banner + primary "Regenerate Draft" + small "Open Stale Draft" link. Both Regenerate paths POST `action=regenerate` to `wizard_draft` and land on the fresh draft, with confirm-before-regenerate
- [x] **Stripe Phase 2 — Checkout Session + promo validation** (commit `95070c5`) — `documents/services/stripe_service.py` with `validate_promo_for_user()` (DB-side `PromoCode` lookup, blocks reuse via `PromoCodeUsage` uniqueness) and `create_checkout_session()` (inline `price_data`, metadata carries `document_slug`, `user_id`, `promo_code_id` for the webhook). Pay page at `/documents/<slug>/pay/` with live AJAX promo validation (400ms debounce, $149 strikethrough → green $99 when valid). Pricing constants `PRICE_FULL_CENTS=14900` / `PRICE_DISCOUNTED_CENTS=9900` in `config/settings.py`. Replaced obsolete `STRIPE_PRICE_*` env vars
- [x] **Stripe Phase 3 — webhook + attachment download** (commit `77d41f1`) — webhook at `/stripe/webhook/` (csrf_exempt, signature-verified) handles `checkout.session.completed`: atomically flips `payment_status='paid'`, sets `paid_at`, records `PromoCodeUsage`, increments `PromoCode.times_used`. Idempotent via new `Document.stripe_session_id` (indexed). `wizard_generate` honors `?download=1` for save-dialog (vs inline preview); paid-state Download button + payment success page both use it. Migration `0014_document_payment_fields`
- [x] **Stripe webhook compatibility hardening** (commits `fa139f2`, `357bbc5`, `820fd5d`) — Webhook view wrapped in defensive try/except so handler exceptions surface as JSON (not Django HTML 500). Worked around stripe-python v10+ removing `dict.get()` from `StripeObject` by re-parsing `request.body` as plain JSON after signature verification
- [x] **Admin reporting for referrals** (commit `ac406b7`, migration `0015`) — `PromoCodeUsage.amount_cents` captures the actual sale price at usage time; settings `PARTNER_CUT_PERCENT=20` (referrer earns $19.80 on each $99 sale). PromoCode admin list shows Sales count + Total revenue + Partner cut as sortable annotated columns. New PromoCodeUsage admin page with date hierarchy, code/referrer filters. CSV export action on both pages — selected rows → "Action" dropdown → download payout sheet
- [x] **Stripe Phase 4 + AI abuse limits combined** (commit `6e7179d`, migration `0016`) — Per-document AI quota: 3 calls free, 150 after payment (counter resets to 0 on payment via webhook). Counted: story extraction, draft regeneration, addendums (court-lookup fallback NOT counted). Live counter badge on draft page (yellow at 1 left, red at 0). Free-doc cap of 2 in-flight drafts per user (paid + finalized don't count, staff exempt). Document `locked_at` field set by Finalize & Download flow → status='finalized' + read-only across all wizard step POSTs (lock-blocked via `_check_locked_redirect()` helper). Two-button download UX on draft page for paid docs: Preview clean PDF (no lock) vs Finalize & Download (confirm dialog → lock → save dialog)
- [x] **Stale-draft view block + one-step undo** (commit `ecdbfe4`, migration `0017`) — Stale drafts can no longer be opened: `wizard_draft` GET redirects to Step 7 when wizard data was edited after the last draft write (locked docs exempt). Step 7 banner is bigger and the "Open Stale Draft" button removed entirely; only "Regenerate Draft" remains. `Document.previous_factual_allegations_json` snapshots the old draft on each regenerate. New `wizard_draft_undo` view + button on draft page lets user restore the previous version (single-use; snapshot cleared after restore). `Document.has_undo()` helper for templates
- [x] **Dark-mode outline button contrast** (commit `1d20253`) — Wizard "Add Evidence", "Add Defendant", "Add Claim", "Restore previous draft", and Back/Cancel buttons were nearly invisible against the dark theme's `#1a1a2e` background because patriot-blue (`#002868`) is too dark. Added `[data-theme="dark"] .btn-outline-{primary, secondary, warning, danger, info}` overrides: bright accent color, 2px border, subtle filled tint at rest, fully filled on hover. Light mode unchanged
- [x] Migrations through `0017_document_previous_draft` (accounts: `0001_initial`)

### Open
- [ ] **Self-serve partner dashboard** at `/partner/` — referrers log in to see their own codes, sales count, gross revenue, partner cut earned, and payout history. Foundation already in place (per-code revenue and `PayoutRequest` model); this is the UI layer. See Pending Roadmap §5
- [ ] **Landing page CMS** — `public_pages` is currently a stub
- [ ] Per-claim case law selection UI (Option B — let users curate which cases apply to which claims rather than auto-pick by amendment). Only worth building once we see whether users actually want curation; the auto-pick covers most auditor cases
- [ ] Playwright/Selenium browser tests for JS interactions (Alpine cards, timestamp spinner, draft textareas, voice button, addendum modal)
- [ ] Switch Stripe to **Live mode** when ready to take real payments — generate live API keys, create a separate live webhook endpoint, update `STRIPE_*` env vars on Render. The code path is identical; only env vars change

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
- `0012_wizardsession_story_addendums` — adds `WizardSession.story_addendums` JSONField (audit trail of per-category addendums)
- `0013_document_factual_allegations_drafted_at` — adds the timestamp used by stale-draft detection
- `0014_document_payment_fields` — adds `Document.stripe_session_id` (indexed, for webhook idempotency) and `Document.paid_at`
- `0015_promocodeusage_amount_cents` — adds `PromoCodeUsage.amount_cents` to capture the actual sale price for partner-cut accounting
- `0016_document_ai_quota_lock` — adds `Document.ai_calls_used` (PositiveInt, default 0) and `Document.locked_at` (DateTime, null)
- `0017_document_previous_draft` — adds `Document.previous_factual_allegations_json` and `previous_factual_allegations_drafted_at` for the one-step regenerate undo

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

### Voice Dictation (`base.html` + Alpine helper)
- `withVoice(propName)` is a global Alpine helper defined in `base.html`. Mix it into any component to add Web Speech recognition that writes finalized transcripts into a named string property.
- Pattern: `x-data="Object.assign({ story: '' }, withVoice('story'))"` then bind a button to `@click="toggleVoice()"` and `:class` off `voiceActive`. The component will gracefully hide the button when `!voiceSupported`.
- Currently wired into: the main story textarea (`wizard_story.html`) and the addendum modal (`wizard_summary.html`).
- Browser support: Chrome/Edge desktop only at the time of writing — Safari/Firefox don't expose `webkitSpeechRecognition`. Hidden button is the correct UX, not a fallback.

### Story Addendums (`documents/services/addendum_service.py`)
- After extraction, the user can add details on top of what GPT got — without re-running the full extraction (which would clobber their manual edits).
- 9 categories: `incident`, `defendants`, `claims`, `evidence`, `witnesses`, `damages`, `plaintiff`, `relief`, `prior_complaints`.
- Per category: snapshot current model state → send `(snapshot + addendum_text)` to GPT-4o → merge GPT's response into the related models **non-destructively**.
- One-to-one models (PlaintiffInfo, IncidentOverview, Damages, ReliefSought, PriorComplaints, GovernmentEntity): update fields where GPT returned a non-null value. Skips user-controlled fields like `court_confirmed`.
- List models: match by stable key (defendants by name, claims by amendment, evidence by URL or type+description prefix, witnesses by name). Existing rows are NEVER deleted — only updated or appended-to.
- Audit trail: each addendum is appended to `WizardSession.story_addendums` (JSONField) with timestamp, category, raw text, and GPT response.
- After merge, the corresponding section of `WizardSession.ai_analysis` is refreshed so the next addendum sees the latest snapshot.
- View: `wizard_addendum` (POST-only, `/documents/<slug>/wizard/addendum/`). Form fields: `category`, `text`. Returns to summary page with a flash message.
- Summary page (`wizard_summary.html`): per-item "Add details" / "Add more" buttons (color-coded by status: red=missing, amber=partial, gray=found) plus an "Add details about something else" picker for categories not surfaced inline (relief, prior complaints, contact info, gov entity).

### Stripe Integration (`documents/services/stripe_service.py`)
- **Pricing:** one product, `$149` full price, `$99` with valid promo code. Constants `PRICE_FULL_CENTS=14900` / `PRICE_DISCOUNTED_CENTS=9900` in `config/settings.py`.
- **Discount mechanism:** validated against our own `documents.PromoCode` table (NOT Stripe Coupons — keeps referrer attribution simple via `PromoCode.created_by`). Final amount is passed inline to Checkout via `price_data`, so no Stripe Product/Price needs to be pre-created.
- **`validate_promo_for_user(code, user)`** returns `{valid, cents, original_cents, message, code}`. Blocks reuse via existing `PromoCodeUsage.unique_together(promo_code, user)`. Honors `discount_type` of `percent`, `fixed`, or `free`.
- **`create_checkout_session(document, user, code, request)`** — creates the Stripe Checkout Session, attaches `metadata={document_slug, user_id, promo_code_id}` for the webhook to pick up.
- **Webhook** at `/stripe/webhook/` (csrf_exempt, mounted in `config/urls.py`): `construct_event()` verifies signature with `STRIPE_WEBHOOK_SECRET`; `handle_checkout_completed()` runs in a single transaction, sets `payment_status='paid'` + `paid_at` + `stripe_session_id`, then creates `PromoCodeUsage` and increments `PromoCode.times_used` if a code was used.
- **Idempotency:** `Document.stripe_session_id` is checked first — duplicate webhook delivery short-circuits without re-flipping status. Won't downgrade a `finalized` doc back to `paid`.
- **Subscribed events:** `checkout.session.completed` (the only one that matters today), `checkout.session.expired` (logged, no-op).
- **Pay button** lives on the draft page: unpaid sees outlined "Preview (watermarked)" + primary "Pay & download clean PDF"; paid sees primary "Download clean PDF" linking to `wizard_generate?download=1`. Live promo code validation via `/pay/validate-promo/` (400ms debounce).
- **Referrer foundation:** every `PromoCode` has a `created_by` user and every sale lands a `PromoCodeUsage` row linking code → user → document. Per-referrer revenue is queryable today; the partner dashboard (Pending §5) is the UI on top of this.

### AI Quota + Document Locking (`documents/services/ai_quota.py`)
- **Per-document AI quota** — `consume_ai_call(document)` atomically increments `Document.ai_calls_used`, raises `QuotaExceeded` if over limit. Counted call types: story extraction (`wizard_story` POST analyze), draft regeneration (`wizard_draft` POST `action=regenerate` AND initial GET-time generation), addendums (`wizard_addendum` POST). Court-lookup fallback intentionally skipped — automatic and small.
- **Limits** — `AI_QUOTA_FREE=3` for unpaid drafts, `AI_QUOTA_PAID=150` for paid docs. Counter resets to 0 on payment via `handle_checkout_completed` so paid users get a fresh 150-call budget. Note the free budget is intentionally tight — typical unpaid path is 1 call (extraction) + 1 call (initial draft generation) leaving 1 spare for an addendum or a single regenerate before the paywall kicks in.
- **Free document cap** — `document_create` view checks `Document.objects.filter(user=u, payment_status='draft').count() >= settings.FREE_DOCS_PER_USER` (default 2). Staff and superusers exempt.
- **Quota UX** — `Document.ai_quota_state()` returns `{used, limit, remaining, exhausted, is_paid}`. Live counter badge on `wizard_draft.html` turns yellow at 1 left, red at 0. When exhausted on unpaid: redirect to `/pay/` with upgrade message. When exhausted on paid: warning saying "Finalize & download to use it, or contact support."
- **Document locking** — `Document.locked_at` (DateTime null=True); `Document.is_locked()` helper. Set by `wizard_generate?finalize=1&download=1` flow when `payment_status='paid'`. Confirms via JS dialog: "Finalizing will lock this document. You won't be able to edit it or run any more AI calls. Are you sure?"
- **Lock-blocking** — `_check_locked_redirect()` helper returns a redirect to `wizard_draft` with a flash if the doc is locked; called at the top of every wizard step POST (1-6), `wizard_caselaw_strategy` POST, `wizard_story` POST, `wizard_addendum`, and `wizard_draft` POST. GET requests still work (read-only viewing). Locked-state UI on draft page: banner + Save/Re-draft buttons hidden + "Re-download PDF" replaces "Finalize & Download". Lock icon on Finalized status badge in documents list.

### One-step Undo of Regenerate (`documents/views.py:wizard_draft_undo`)
- **Goal:** when a regenerate produces output the user doesn't like, let them roll back to what they had before the regenerate. Single level deep — one click of undo, then snapshot is consumed.
- **Snapshot** — `_snapshot_current_draft(doc)` copies the current `factual_allegations_json` into `previous_factual_allegations_json` and stamps `previous_factual_allegations_drafted_at`. Called inside `wizard_draft` POST `action=regenerate` immediately before `_save_paragraphs(doc, new_paragraphs)`. NOT called for the GET-time initial generation (nothing to roll back to).
- **Restore** — `wizard_draft_undo` view (POST-only at `/documents/<slug>/wizard/draft/undo/`): swaps `previous_*` back to current, clears the snapshot, refuses to act on locked docs.
- **UI** — `Document.has_undo()` returns True when a non-empty snapshot exists. Blue info banner on draft page: "A previous draft is saved from before your last regenerate. [Restore previous draft]" with confirm dialog.

### Stale-draft View Block (`documents/views.py:wizard_draft`)
- **Goal:** prevent users from looking at outdated drafts after editing wizard data.
- `wizard_draft` GET: when `paragraphs` exists AND not locked AND `_is_draft_stale(doc, session)`, redirect to Step 7 with warning flash. Locked docs are exempt — their draft is by definition the final version, even if `wizard_session.updated_at` would otherwise mark it stale.
- Step 7 template: when stale, the "Open Stale Draft" button is gone — only the warning banner + "Regenerate Draft" button remain. Banner uses heading + body (not a one-line note) so it's harder to miss.
- Regenerate path is allowed on stale docs (it FIXES the staleness).

### Stale Draft Detection (`documents/views.py:_is_draft_stale`)
- Goal: when a user edits any wizard step (Step 2 time, Step 3 defendants, Step 4 claims, etc.) AFTER the AI has drafted the factual allegations, the cached narrative paragraphs are out of date.
- `Document.factual_allegations_drafted_at` is set whenever `_save_paragraphs()` is called (initial draft, regenerate, or save edits).
- `_is_draft_stale(doc, session)` returns True when `wizard_session.updated_at > factual_allegations_drafted_at`.
- Step 7 surfaces a yellow banner + Regenerate Draft button BEFORE the user opens the (potentially outdated) draft. Draft page also shows the banner.
- Other structural sections (caption, parties, claims, evidence, prayer) are NOT cached — they render live from current models, so they were never stale.
- `complaint_drafter.py` system prompt is explicit: structured wizard data (date/time/address/names/badges) reflects the user's latest edits and wins on conflict; the story is only the source of truth for sequence + what was said.

### Step 2 Datetime UX (`templates/documents/wizard_step2.html`)
- **Quick-chip buttons**: Date — Today / Yesterday / Last week / A month ago. Time — Now / Morning (9) / Afternoon (2) / Evening (6) / Night (10).
- **Live preview** under each field: "Saturday, May 4, 2024 at 1:00 PM" — tells the user what's selected without staring at `2024-05-04`.
- **Flatpickr popups**: click the date input → calendar with `maxDate=today`; click the time input → spinner with up/down arrows on hours, minutes (5-min increments), and AM/PM. Loaded from CDN (~15KB gzipped).
- Visible value uses friendly format; the original input still submits `Y-m-d` and `H:i` to the backend (unchanged from server's perspective).
- Chips set both Alpine state AND the Flatpickr instance via `setDate(value, false)` so the popup stays in sync.
- Dark-mode CSS overrides match the popup to the app theme.

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

What it **doesn't** cover: Alpine.js interactions (Playwright/Selenium later), real GPT quality (manual sanity), Stripe webhook flow, finalize/lock, undo, stale-draft block, free-doc cap, AI quota enforcement. These shipped after the original test suite was written and have been validated manually on production only — adding pytest coverage for them is worth a future session.

---

## Render Deployment Reference

**The app is already live on Render at `file1983.com`** — this section is reference material for re-creating the service or onboarding a new environment. Day-to-day deploys happen automatically when commits land on `master`.

**Code-side prep** (commit `0d4212e`): `docker-entrypoint.sh` runs migrate + collectstatic + gunicorn on `$PORT`; `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, secure cookies, and SSL redirect are all wired in `config/settings.py` for `DEBUG=0`.

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
   - `STRIPE_SECRET_KEY=sk_test_...` (sandbox) — required for `/pay/` to function
   - `STRIPE_PUBLISHABLE_KEY=pk_test_...`
   - `STRIPE_WEBHOOK_SECRET=whsec_...` — created in Stripe Dashboard → Developers → Webhooks (or "Event destinations" in the new UI). Endpoint URL: `https://file1983.com/stripe/webhook/`. Subscribe to events `checkout.session.completed` and `checkout.session.expired`. Without this var set, the webhook returns 500 and `payment_status` will not auto-flip to `paid`
4. **Static files + migrations** — handled automatically by `docker-entrypoint.sh` on every container start (migrate → collectstatic → gunicorn). With Docker runtime on Render there is no separate Build Command to configure; do **not** also set one in the dashboard or it will run twice and slow deploys. `whitenoise` is already in middleware and `STATICFILES_STORAGE` is `CompressedManifestStaticFilesStorage`.
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

## Roadmap Status

> **Heads-up on app placement:** `PromoCode`, `PromoCodeUsage`, and `PayoutRequest` all live in **`documents/models.py`** (not `accounts/`). The `accounts` app only has `User`, `Subscription`, `DocumentPack`, `SiteSettings`, `LegalDocument`. Earlier drafts of this doc said `accounts.PromoCode` / `accounts.PayoutRequest` — those were wrong.

**Shipped:** pricing model, Stripe Checkout (Phases 2 + 3), Stripe Phase 4 (finalize + lock on download), per-document AI quota, document locking. See **Build Status → Done** and **What's Built — Detail** for commit SHAs and full shape.

**Stale schema cleanup:** the unused `price_3pack` / `price_monthly` / `price_annual` fields on `accounts.SiteSettings` are not in any code path. Safe to drop in a future migration when convenient.

### Open: Self-serve partner dashboard
**Decided:** referrer cut is **20% of $99 = $19.80 per sale** (`settings.PARTNER_CUT_PERCENT=20`).

**Foundation already shipped (commit `ac406b7`):**
- Every `PromoCode` has `created_by` set to a referrer User
- Every sale through that code creates a `PromoCodeUsage` row linking code → buyer → document, with `amount_cents` capturing the actual sale price
- Admin already shows per-code revenue + partner cut + CSV export. You can run a payout cycle today entirely through the admin.

**What's left to build for `/partner/`:**
- A view that lets a referrer log into the regular auth, then visit `/partner/` and see their own stats: total sales count, total gross revenue (sum of `amount_cents`), total cut owed (`× 0.20`), recent sales table (date / buyer email / amount / cut), and payout history (existing `documents.PayoutRequest` model).
- A "Request payout" button — creates a `PayoutRequest` row in `pending` status; admin reviews and marks `approved`/`paid` manually.
- Auth gate: simplest is a `User.is_revenue_partner` BooleanField (one migration), then `@user_passes_test(lambda u: u.is_revenue_partner or u.is_staff)` on the partner views. Or use a `Group`.

**Open questions before building:**
- Should partners see WHO bought (buyer email/name) or just aggregate stats? Privacy vs transparency tradeoff.
- Should they be able to download their own CSV, or only request payouts through admin?
- Do partners need a way to share their referral link directly (e.g. `https://file1983.com/?ref=PARTNERCODE` that pre-fills the promo code at checkout)?

### Working agreement
User wants to take features one at a time, structured. Don't bundle. The next Claude session should ask the user which of these to tackle first:
- Partner dashboard (above)
- Landing page CMS (`public_pages` is currently a stub)
- Switch Stripe to live mode
- Something else the user has in mind

Don't assume — ask.

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
