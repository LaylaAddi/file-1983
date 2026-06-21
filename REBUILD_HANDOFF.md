# 1983 Law — Project Handoff

## The App
A Django web app that guides users through building a **Section 1983 civil rights complaint**
against government officials. Target users: First Amendment auditors, citizens documenting
police misconduct, unlawful arrest, excessive force, retaliation for recording in public.

Flow: User tells their story → AI extracts structured data → wizard lets user review/edit
each section → final review → AI drafts factual allegations → user reviews/edits draft → PDF download → Stripe payment to remove draft watermark.

---

## Where we are right now (read this first)

**Status:** MVP is feature-complete and live on Render at `auditfile1983.com` (Stripe in sandbox/test mode). `file1983.com` 301-redirects to `auditfile1983.com` via Django middleware. Recent test users have completed full purchase flows successfully. Self-serve partner dashboard with shareable referral links and self-request partnership flow are live.

**What works end-to-end today:**
- Story → wizard → AI draft → preview PDF → pay $149 (or $99 with promo code) → webhook flips status → **explicit two-checkbox confirmation page** (acknowledge complete + acknowledge AI-disclaimer) → finalize lock + clean PDF download. Re-download stays available; the watermark is gated by lock (not payment), so paid-but-unlocked previews are still watermarked. Prevents preview-abuse.
- After lock, **all wizard edit pages** (story, summary, addendum, steps 1–7, case law) bounce to the draft page with a flash on both GET and POST. Lock is per-document; other docs in the same account stay editable. The documents-list row swaps Continue/Edit buttons for Download PDF + View when the doc is locked.
- **Signup TOS / Privacy gate.** Two required checkboxes on `/accounts/register/` plus a prominent AI / not-a-lawyer warning. Acceptance stamped on the User with `tos_accepted_at`, `tos_accepted_version`, `privacy_accepted_at`, `privacy_accepted_version`.
- **Re-acceptance gate.** `RequireLegalAcceptanceMiddleware` redirects any logged-in user whose stored version doesn't match `settings.TOS_VERSION` / `PRIVACY_VERSION` to `/accounts/accept-terms/`. Bumping the env var forces every existing user to re-accept on next request.
- **DB-editable legal copy.** `LegalDocument` rows (terms, privacy, disclaimer, cookies) carry `content` (HTML), `version`, and `effective_date`. Editable in admin at `/<ADMIN_URL>/accounts/legaldocument/`.
- Promo codes track referrer attribution; admin shows per-code revenue and the partner cut
- Partner dashboard at `/partner/` with sales table (buyer name+email visible to partner), payout request flow with email to admin, balance adjustments, shareable `?ref=CODE` links that auto-pre-fill the promo at checkout
- Users can request partnership from their profile; admin approval auto-flips the flag AND creates a PromoCode in one click
- AI quota limits prevent runaway OpenAI spend on a single document
- Free-doc cap stops users from creating unlimited drafts
- One-step undo restores the previous draft after a regenerate
- Stale-draft block forces users to regenerate before viewing an outdated draft
- Password reset works via SMTP (Namecheap Private Email, `rights@auditfile1983.com`); confirm page logs out current session and shows which account is being reset
- **Live RSS news widget** on the landing page pulls hourly from ACLU, EFF, FIRE, Institute for Justice, SCOTUSblog, Reason via a `fetch_news` management command on a Render Cron Job. Each item opens in a new tab; admin can hide off-topic rows with a checkbox.
- **`/sitemap.xml`** advertises all 8 public pages + 4 legal pages + any published `CivilRightsPage` rows for search engines. `robots.txt` already references it.
- **Admin-editable footer contact** — `SiteSettings.contact_email` / `contact_phone` with independent visibility flags render in the footer's brand column as `mailto:` / `tel:` links.

**Latest commits this session (most recent on top), on branch `claude/gracious-ritchie-ckyr9t` (merged into `master`):**
- Brute-force/login hardening (`django-axes` + `django-ratelimit`), the register-view 500 fix for the multi-backend `login()` call, a `revoke_testers` management command, a wizard Step 1 fix so overriding a found court also re-exposes the address fields (not just a blind court-name text box), the stale-incident/government-entity-data fix on story re-analysis, and the new per-document AI-call cooldown — all documented in their respective detail sections above. A cosmetic migration-drift cleanup (`documents/0025_alter_partneradjustment_id_and_more`) also shipped this session.

**Earlier commits this session (most recent on top), on branch `claude/awesome-wozniak-rqxq2a`:**
- `bd6692c` — **Format plaintiff phone on the PDF.** New `documents/templatetags/phone_filters.py` with a `format_phone` filter — formats a raw 10-digit (or 11-digit with leading `1`) phone string as `(XXX) XXX-XXXX` for display; anything else (already formatted, international, blank) passes through unchanged. `Plaintiff.phone` is a free-text field, so a user-entered `7162380814` was rendering unformatted on the complaint PDF. Wired into `templates/documents/pdf/complaint.html` only — the one place phone is shown on the PDF
- `ca5cde4` — **Low-confidence warning banner for unverified agency names (Step 3).** New `documents/views._looks_like_unverified_agency(agency_name, city)` heuristic: returns False if blank, if the agency name contains the incident city, or if it already names `sheriff` / `state police` / `highway patrol` / `state patrol` / `county`; otherwise True if it contains `police` or `department`. GPT has no real law-enforcement-agency dataset (unlike the court/county lookups), so for small/rural towns it tends to fabricate a generic department name instead of the county sheriff or state police that more likely covers the area. `wizard_step3` GET computes `incident_city` and an `unverified_agency` flag per defendant; `wizard_step3.html` mirrors the same heuristic client-side in Alpine (`isUnverifiedAgency()`) so the banner reacts live as the user edits the Agency field, prompting them to double-check before filing
- `c33b753` — **ZIP-based county lookup.** New bundled dataset `documents/services/county_data/us_zip_county.json` (~33k ZIP→{county,state} entries, derived from US Census ZCTA data via `scpike/us-state-county-zip`), checked first in `CountyLookupService.lookup_county()` ahead of the city/state dataset, since ZIP also covers unincorporated communities (no city government, so missing from the city-name dataset) that still have their own ZIP — e.g. Van Wert, GA (unincorporated, Polk County, shares ZIP 30153 with Rockmart). New `IncidentOverview.zip_code` field (migration `documents/0024_incidentoverview_zip_code`); Step 1 gained a ZIP input wired into the AJAX court/county lookup
- `3fddd77` — **Stale county value + dynamic Google Maps link fix.** Step 1's Alpine `doLookup()` never cleared `this.county` before a new lookup, so a previous city/state's county lingered on screen even when the new lookup found nothing. Fixed by resetting `county` at the start of every lookup. Google Maps link on Step 1 is now a computed `mapsUrl` property built from the current city/state/ZIP instead of a static homepage link
- `14fd0e5` — **Static city/state county lookup replaces GPT's free-text guess.** New `documents/services/county_lookup_service.py` + bundled `documents/services/county_data/us_city_county.json` (~29.7k incorporated US cities, MIT-licensed from `kelvins/US-Cities-Database`). GPT's county guess from the story alone has no real data behind it and is unreliable for small/obscure places — extraction and Step 1's auto-heal now trust the static lookup and leave county blank rather than show a confident-looking but unverified guess
- `3a09656` — Step 1 POST now persists any city/state correction the user makes (previously the override only fed the client-side court lookup and got discarded, so Step 2 showed stale GPT-extracted values)
- `4311e73` — **Searchable federal-court dropdown on Step 1.** `CourtLookupService.get_all_court_names()` (all ~89 distinct court names) feeds an HTML `<datalist>` on the override input, so users can pick from the full list of federal districts or still type their own
- `6a3aead` — **Single-code tester signup.** New `PromoCode.auto_grants_tester` BooleanField (migration `documents/0022_promocode_auto_grants_tester`). When a user enters such a code in the Referral Code field on `/accounts/register/`, `RegisterForm.save()` marks them `is_tester=True` + stamps `tester_granted_at`, and `accounts.views.register` stashes the canonical code in `request.session['referral_code']` so the existing `/pay/` pre-fill auto-applies it at checkout. Tester enters one code, gets both ends — autofill/badge + free Stripe Checkout — without any admin step. No collision with the partner referral lookup (seeded tester promos have no `created_by` so `_resolve_referrer` doesn't set `referred_by`). `seed_tester_promo` now defaults `auto_grants_tester=True`; PromoCode admin shows the new column + filter
- `1232f98` — **Tester cleanup tooling.** New management command `python manage.py seed_tester_promo` creates a `PromoCode` with `discount_type='free'`, `is_active=True` (default code `TESTFREE-<random6>`); `--code MYCODE` to override, `--deactivate --code MYCODE` to flip `is_active=False`. New UserAdmin bulk action `reset_test_purchases` rolls every paid/finalized doc owned by the selected users back to `'draft'`, clears `paid_at`/`stripe_session_id`/`locked_at`/`finalize_acknowledged_at`/`download_disclaimer_acknowledged_at`, deletes the matching `PromoCodeUsage` rows, decrements `PromoCode.times_used` by the corresponding count. Documents themselves preserved
- `a3713a0` — **`User.is_tester` flag for podcast volunteer testers.** New BooleanField + `tester_granted_at` timestamp on `User`; migration `accounts/0006_user_is_tester`. UserAdmin gets `is_tester` column + filter + a "Tester Access" fieldset + two bulk actions (`mark_as_tester` / `revoke_tester`) so you can flip a cohort with one click. Story-page example-stories gate widened from `is_staff or DEBUG` to `is_staff or is_tester or DEBUG`. Navbar shows a yellow "Test mode" badge (with flask icon, tooltip explains revocation) for testers on md+ viewports. Lower-privilege than `is_staff` — safe to grant unknown users without exposing `/manage-dev/`
- `4e7e858` — **"We're a Tool, Not Your Lawyer"** section on the homepage between Quick Stats and Know-Your-Rights. Three-column cream-background section (Not a law firm / A convenience tool / Consult a lawyer when unsure) with links to the Legal Disclaimer and User Guide pages
- `f456c93` — **User Guide page at `/guide/`** (`public_pages.views.user_guide`). 15-section single-page walkthrough with sticky TOC on lg+ and collapsible `<details>` TOC on mobile. Covers signup → profile → PWA install → quick-add → wizard steps → case law → draft → payment → finalize → re-download → offline + a deliberately-long referrals section (Steps A–E + "common confusion points") because a test user got stuck on `?ref=`. Linked from the navbar user dropdown ("User Guide") and the footer Resources column
- `98d19ea` — Step 7 case-law prompt is now prominent when `caselaw_strategy='none'`: amber-bordered card with gradient header, "Decide before filing" badge, two-paragraph explanation, real patriot-blue "Choose case law strategy" button + small "(or scroll down to continue without it)" hint. Reverts to quiet review-card styling once any strategy is picked
- `95b4608` — Dictation duplication fix + per-chunk delete. `withVoice` refuses to start when `navigator.onLine` is false (Web Speech API uses cloud STT — offline attempts duplicated transcripts). Added `_voiceLastIndex` cursor so a misbehaving engine that resets `resultIndex` can't re-append prior chunks. New `/d/<slug>/q/delete-chunk/` endpoint (`wizard_quick_add_delete_chunk`) re-parses story_text, drops the chunk at the POSTed index, rewrites via `_rebuild_story_text`. Trash icon on every saved chunk card (server POST + confirm prompt) and every queued chunk card (`__outbox.delete`, no server roundtrip)
- `99f76a0` — **Offline support (PWA Phase 1 + 2).** New `templates/service-worker.js` (precaches icons, theme CSS, manifest, `/documents/start/`, `/documents/`, `/accounts/login/`; cache version is `RENDER_GIT_COMMIT[:8]` so every deploy invalidates it; network-first for navigation, cache-first for static assets, /admin /api /stripe excluded). Served from `/sw.js` with `Service-Worker-Allowed: /` via new `service_worker` view; registered from `base.html` on load. `wizard_quick_add` view gained a JSON response path triggered by `Accept: application/json` (returns `{ok, mode, chunk_number, timestamp}`). The quick-add template now intercepts form submits, queues failed/offline saves in IndexedDB (`auditfile-outbox`, store `chunks`, indexed by `doc_slug`), shows queued cards (amber border) at the top of the chunk stack, surfaces Offline / N-queued badges in the header, and drains the outbox on page load + `online` events (reloads on success to refresh from server). Voice dictation still requires network — Web Speech API uses cloud STT on Android Chrome.
- `964f9bc` — Dark-mode chunk fix. Added `[data-theme="dark"]` overrides for `.chunk-item` using the existing `--dark-bg-secondary` / `--dark-text` palette; chunk body text is now readable in the user's dark theme
- `fada669` — PWA opens on the user's active document. New `/documents/start/` view (`pwa_start`) picks the most recent non-finalized document and 302s to its quick-add page; manifest `start_url` updated. Document list card now makes Quick add ("Add to story") the primary action whenever the doc has story content; Continue drops to outlined secondary, Edit story to a muted text link
- `ca4823d` — Read-only chunk stack on the quick-add page. `_parse_story_chunks` splits `story_text` on `--- Added <timestamp> ---` divider lines; template renders three regions: dismissible "How this works" 3-step strip (localStorage-remembered), read-only chunk cards stacked with `#N` badge + timestamp (intro chunk styled with navy left border), and a clearly-separated "Add a new chunk" card with an always-empty textarea (so cursor accidents in prior text are impossible). Post-save flash now reads `Saved chunk #N — keep going, or tap "Review & analyze" when you're done.`
- `4f098c4` — Mobile-only PWA install card on the homepage (`d-lg-none`). Captures `beforeinstallprompt` globally in base.html, exposes a tap-to-install button on Android Chrome, falls back to inline Share → Add to Home Screen instructions on iOS Safari. Hides itself when `display-mode: standalone` (already installed)
- `b224a2d` — Generated PWA raster icons. Rendered `static/images/pwa/{icon-192,icon-512,icon-512-maskable,apple-touch-icon}.png` from `favicon.svg` via `cairosvg`. Maskable variant drops the rounded-corner rect and insets the gavel into the 80% safe zone so Android can crop to any mask shape. Manifest references PNGs first with the SVG as a fallback; `apple-touch-icon` link updated to the 180×180 PNG so iOS Add-to-Home-Screen renders the gavel
- `c46376a` — Quick-add page + PWA manifest. New `/documents/<slug>/q/` (`wizard_quick_add`) mobile-first one-textarea page with voice mic, dual semantics based on `session.ai_extraction_succeeded`: before-analyze appends each chunk to `WizardSession.story_text` with a `--- Added <stamp> ---` UTC timestamp divider; after-analyze routes the submit through `addendum_service.apply_addendum` with a category picker so manual edits in steps 1–7 stay intact. `static/manifest.webmanifest` + `<link rel="manifest">` + `theme-color` + `apple-mobile-web-app-*` meta tags in `base.html`

**Previously deployed (before this session) — see git log for full history. Notable recent ones on `master`:**
- `1b4d4b0` — Admin-editable footer contact (email + phone with hide toggles); migration `accounts/0005_sitesettings_contact`
- `3303b14` — Add `/sitemap.xml` via `django.contrib.sitemaps`
- `d5fbc72` — Terms / Privacy acceptance + AI-disclaimer gates; migrations `accounts/0003_legal_acceptance` + `documents/0021_document_download_disclaimer`
- `85f6d0e` — Gate clean PDF behind lock, not behind payment
- `d8abdc8` — Finalize confirmation page + audit stamp (`Document.finalize_acknowledged_at`)
- `9d808c1` — Canonical-domain redirect; `PRIMARY_DOMAIN` setting

**Settings worth knowing about (all in `config/settings.py`):**
- `PRICE_FULL_CENTS=14900` / `PRICE_DISCOUNTED_CENTS=9900` — list and promo prices
- `PARTNER_CUT_PERCENT=20` — referrer earns $19.80 on each $99 sale
- `PARTNER_MIN_PAYOUT_CENTS=2000` — $20 minimum balance to request payout
- `AI_QUOTA_FREE=3` / `AI_QUOTA_PAID=150` — per-document AI call limits
- `FREE_DOCS_PER_USER=2` — max draft documents in flight per user
- `PRIMARY_DOMAIN='auditfile1983.com'` — canonical host; `CanonicalDomainMiddleware` 301-redirects others to it
- `TOS_VERSION='v1'` / `PRIVACY_VERSION='v1'` — env-overridable. Bump on Render to force every existing user to re-accept on next request (must also bump the matching `LegalDocument.version` in admin).

**Render service inventory (current):**
- **Web service** — Docker, master branch, auto-deploys from `master`. Runs `docker-entrypoint.sh` (migrate + collectstatic + gunicorn).
- **Postgres** — Starter plan, internal connection to the web service.
- **Cron Job — fetch_news** — Docker, master branch. Schedule `0 * * * *`. Command (in Docker Command field): `python manage.py fetch_news`. Needs `DATABASE_URL`, `SECRET_KEY`, `DEBUG=0`, `ALLOWED_HOSTS`, `ADMIN_URL` copied from the web service.

**Active testing setup (the user is recruiting podcast volunteers right now):**
- Free-access promo code `TESTFREE-6B4F54` is seeded on production with `auto_grants_tester=True`.
- Tester enters that code in the **Referral Code** field on `/accounts/register/` → auto-marked `is_tester=True` → gets the "Test mode" navbar badge + example-stories autofill on the wizard story page + the same code stashed in `request.session['referral_code']` so it auto-applies at `/pay/` for $0 Stripe Checkout.
- **End-of-round cleanup workflow:** Admin → Users → check tester rows → bulk action **"Reset test purchases (paid + finalized) on selected users to draft"** → bulk action **"Revoke tester status from selected users"**. Then on Render Shell: `python manage.py seed_tester_promo --deactivate --code TESTFREE-6B4F54` to kill the code so it can't be reused.
- See **Tester onboarding** detail section for the full mechanism (flags, gates, lookups). Don't seed a tester promo with a guessable code (no bare `TESTFREE` — the `<random6>` suffix matters).

**What the next Claude should know about user preferences:**
- User wants step-by-step instructions, not autonomous large changes
- User can't always copy text outside of code blocks — always wrap commands, URLs, codes in triple backticks
- User is on Windows / PowerShell; chained commands need newlines, not `&&`
- User does NOT want to use terminal heavily — prefer admin UI and clickable URLs
- User tests on production Render with a few test accounts (no local Docker setup)
- Workflow: develop on `claude/<short-description>` branch → push → user merges to master locally → Render auto-deploys

**Mobile / PWA (shipped this session — see commits above):**
- Installable PWA with `manifest.webmanifest`, raster icons (192/512/maskable/180-apple), mobile install card on the homepage that wires `beforeinstallprompt` (Android) and shows Share→Add-to-Home-Screen instructions (iOS).
- Tapping the home-screen icon lands the user directly on the quick-add page of their most-recent open document (`/documents/start/` chooses the doc + redirects).
- **Quick-add page** (`/documents/<slug>/q/`) is the field-capture UI. Before analyze: each save appends a timestamped chunk to `story_text` (read-only chunk stack visible above the input). After analyze: same UI, but submits route through the existing `addendum_service` so steps 1–7 edits stay intact.
- **Offline:** service worker caches app shell + key navigation targets; IndexedDB outbox queues failed/offline saves and drains automatically on `online` + page load. Voice dictation still requires network (Web Speech API limit, not a service-worker issue).

**Likely next features (user's open roadmap, prioritized):**
1. Landing page CMS — `public_pages.CivilRightsPage` and `PageSection` models already exist with the right shape; just need admin polish + a few seeded pages. Primary domain is auditfile1983.com so this is the homepage users see.
2. Switch Stripe to **Live mode** when ready to take real payments — generate live keys, create a live webhook endpoint at `https://auditfile1983.com/stripe/webhook/`, swap `STRIPE_*` env vars on Render.
3. Optional mobile polish: native Capacitor wrapper for App Store / Play Store distribution + real push notifications. Open question, not committed — see Roadmap → Open below for the trade-off summary. Capacitor is the lowest-friction path since the app is HTML/CSS/JS, but adds $25 Play + $99/yr Apple fees and ongoing native-build overhead.
4. Optional polish: per-claim case-law selection UI, Playwright/Selenium browser tests, more admin niceties.

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
- **`auditfile1983.com`** — primary (canonical) host that users land on
- **`file1983.com`** — secondary; 301-redirects to `auditfile1983.com` via `CanonicalDomainMiddleware` (controlled by `PRIMARY_DOMAIN` setting / env var, defaults to `auditfile1983.com`)
- Both domains are attached to the same Render web service. The redirect happens in Django, NOT at Namecheap; flipping `PRIMARY_DOMAIN` env var on Render reverses the direction with no DNS changes
- Email: `rights@auditfile1983.com` via Namecheap Private Email (`mail.privateemail.com`, port 587, TLS). The mailbox `rights@file1983.com` also exists from earlier setup but isn't currently used

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

## Environment Variables (`.env` file in dev / Render env vars in prod)
```
SECRET_KEY=
DEBUG=1                          ← 0 in production
ALLOWED_HOSTS=localhost,127.0.0.1   ← in prod: file1983.com,www.file1983.com,auditfile1983.com,www.auditfile1983.com,<app>.onrender.com
DATABASE_URL=postgresql://postgres:postgres@db:5432/file1983
ADMIN_URL=manage-dev/

OPENAI_API_KEY=                  ← required for extraction, court lookup fallback, draft generation

STRIPE_SECRET_KEY=               ← sk_test_... (sandbox) or sk_live_...
STRIPE_PUBLISHABLE_KEY=          ← pk_test_... or pk_live_...
STRIPE_WEBHOOK_SECRET=           ← whsec_... from Stripe Dashboard webhook destination

# Email — settings.py auto-picks SMTP backend in prod (DEBUG=0), console in dev.
# So in prod you DO NOT need to set EMAIL_BACKEND.
EMAIL_HOST=mail.privateemail.com
EMAIL_PORT=587
EMAIL_HOST_USER=rights@auditfile1983.com
EMAIL_HOST_PASSWORD='<wrap-in-single-quotes-if-special-chars>'
DEFAULT_FROM_EMAIL=File 1983 <rights@auditfile1983.com>   ← display name format

# Optional. Defaults to 'auditfile1983.com'. Flip to switch canonical domain.
PRIMARY_DOMAIN=auditfile1983.com

# Optional. Defaults to DEFAULT_FROM_EMAIL. Where partnership requests + payout
# requests are emailed.
PARTNER_PAYOUT_NOTIFY_EMAIL=
```

---

## URL Map
```
/                                           → public_pages:home (landing page with hero, mobile-only PWA install card under hero, Quick Stats, "We're a Tool, Not Your Lawyer" disclosure, featured articles, live RSS news widget, key rights, resources)
/guide/                                     → public_pages:user_guide — 15-section walkthrough (account → profile → PWA install → quick-add → wizard → case law → draft → payment → finalize → offline → referrals → FAQ) with sticky TOC. Linked from navbar user dropdown and footer Resources column. Deep-link directly to a section via #anchor (e.g. /guide/#referrals)
/sitemap.xml                                → Django sitemaps framework — static pages + legal pages + published CMS pages
/robots.txt                                 → User-agent: * / Disallow /accounts/ /documents/ / advertises /sitemap.xml
/sw.js                                      → service worker (rendered from `templates/service-worker.js` via `documents.views.service_worker`; cache_version baked in at deploy time; `Service-Worker-Allowed: /` header so it claims the whole origin)
/legal/terms/                               → Terms of Service rendered from LegalDocument(doc_type='terms')
/legal/privacy/                             → Privacy Policy rendered from LegalDocument(doc_type='privacy')
/legal/disclaimer/                          → Legal Disclaimer (hardcoded template — no LegalDocument row seeded yet)
/legal/cookies/                             → Cookie Policy (hardcoded template — no LegalDocument row seeded yet)
/accounts/register/                         → register; two required checkboxes (TOS + Privacy), AI/not-a-lawyer warning, stamps tos/privacy_accepted_at + version on User
/accounts/login/                            → login
/accounts/logout/                           → logout
/accounts/accept-terms/                     → re-acceptance gate. Logged-in users with stale tos_accepted_version / privacy_accepted_version are redirected here by RequireLegalAcceptanceMiddleware. Two checkboxes required to continue; logout link for "I do not agree"
/accounts/profile/                          → profile (full address, incomplete-profile banner, referral block — partner sees codes+share links; non-partner sees Request Partnership form)
/accounts/profile/request-partnership/      → POST: creates PartnershipRequest + emails admin
/accounts/pricing/                          → pricing stub
/accounts/password-reset/                   → password reset flow (logs out current session on confirm page)
/documents/                                 → document list. Locked docs show Download PDF + View buttons. Open docs surface "Add to story" (Quick add) as the primary action with Continue + Edit story below. Admin sees Delete button
/documents/start/                           → PWA `start_url` target. `pwa_start` view picks the user's most recent non-finalized document and 302s to its `/q/` page; falls back to `/documents/` when there are none
/documents/new/                             → create document (profile gate)
/documents/<slug>/delete/                   → POST-only, staff-only, deletes document
/documents/<slug>/q/                        → mobile quick-add page (`wizard_quick_add`). Read-only stack of saved chunks + always-empty new-chunk textarea + voice mic. Pre-analyze: appends to `story_text` with `--- Added <UTC stamp> ---` divider. Post-analyze: shows category picker, submits route through `addendum_service`. POST with `Accept: application/json` returns `{ok, mode, chunk_number, timestamp}` (used by the IndexedDB outbox to replay offline saves). Offline saves queue locally and drain on `online` events. Every chunk card has a trash icon (server POST for saved chunks, IndexedDB delete for queued)
/documents/<slug>/q/delete-chunk/           → POST-only (`wizard_quick_add_delete_chunk`). Takes `idx` (0-based position from `_parse_story_chunks`), drops that chunk, rewrites story_text via `_rebuild_story_text` (inverse of the parser). Lock-aware, range-checked, redirects back to `/q/`
/documents/<slug>/wizard/                   → story input page (with Dictate voice button). Editing here clobbers manual wizard edits on re-analyze — use `/q/` for additive chunks instead
/documents/<slug>/wizard/summary/           → post-extraction summary (per-item "Add details" + "something else" addendum picker)
/documents/<slug>/wizard/addendum/          → POST: per-category story addendum (voice-friendly), non-destructive merge into wizard models. The quick-add page's post-analyze submits go through the same `addendum_service`
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
/documents/<slug>/wizard/generate/          → WeasyPrint PDF. Watermarked unless doc.is_locked() (so paid+unlocked previews are still watermarked — closes preview-abuse). ?download=1 forces save dialog. The old ?finalize=1 query path was removed; locking now lives at /finalize/.
/documents/<slug>/finalize/                 → GET: confirmation page with TWO required checkboxes — (1) "I confirm complete + understand editing locks" and (2) AI-disclaimer: "I understand this was AI-assisted, you're not my lawyer, I'll consult an attorney if unsure." POST: stamps Document.finalize_acknowledged_at AND download_disclaimer_acknowledged_at AND locked_at, flips status to 'finalized', then redirects to wizard_generate?download=1. Refuses to act on already-locked docs (bounces to draft) and unpaid docs (bounces to /pay/)
/documents/<slug>/pay/                      → Pay $149 (or $99 with promo code) — creates Stripe Checkout Session
/documents/<slug>/pay/validate-promo/       → AJAX: GET ?code=XYZ → live promo validation for the pay page
/documents/<slug>/pay/success/              → Stripe success_url; offers clean PDF download
/documents/<slug>/pay/cancel/               → Stripe cancel_url; flashes message + redirects to draft
/stripe/webhook/                            → Stripe webhook endpoint (csrf_exempt, signature-verified). Handles checkout.session.completed
/documents/lookup-district-court/           → AJAX: GET ?city=&state= → court name JSON
/partner/                                   → Partner dashboard (gated by is_revenue_partner or is_staff). Sales, cut earned, adjustments, payouts
/partner/request-payout/                    → POST: creates PayoutRequest + emails admin
/api/v1/token/                              → JWT obtain
/api/v1/token/refresh/                      → JWT refresh
/<ADMIN_URL>/                               → Django admin

Note: Any URL with `?ref=CODE` (e.g. `/?ref=ALICE10`) gets captured by
CaptureReferralMiddleware and stored in session. Pre-fills the promo input on
`/pay/` and the referral input on `/accounts/register/`.
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
- [x] Migrations through `documents/0022_promocode_auto_grants_tester` (accounts through `0006_user_is_tester`, public_pages through `0002_newsitem`)
- [x] **Terms of Service / Privacy acceptance + AI-disclaimer gates** (commit `d5fbc72`) — see "What works end-to-end" above for the full shape. Two required checkboxes on register, re-acceptance gate via middleware, DB-editable copy, four audit fields on User, second AI-disclaimer checkbox on /finalize/, /accounts/accept-terms/ view + template, footer Terms/Privacy/Disclaimer links wired
- [x] **Lock-aware documents list** (commit `ff77866`) — locked docs show Download PDF + View instead of Continue/Edit
- [x] **Rebrand to AuditFile 1983** (commit `0e1387e`, migration `accounts/0004`) — seeded legal copy, SiteSettings defaults, "AuditFile 1983 Parties" definition with owners/officers/employees/contractors/agents/representatives/affiliates/successors
- [x] **Live RSS news widget** (commits `ed770d7`, `3d144de`, migration `public_pages/0002`) — `NewsItem` model, `fetch_news` management command, 6 curated feeds (ACLU, EFF, FIRE, IJ, SCOTUSblog, Reason), hourly Render Cron Job, admin hide-toggle
- [x] **`/sitemap.xml`** (commit `3303b14`) — Django sitemaps framework, 12 URLs (8 static + 4 legal) + auto-included published CMS pages
- [x] **Admin-editable footer contact** (commit `1b4d4b0`, migration `accounts/0005`) — email + phone with independent visibility flags
- [x] **Installable PWA + mobile install card** (commits `c46376a`, `b224a2d`, `4f098c4`) — `static/manifest.webmanifest` with PNG icon set under `static/images/pwa/` (192, 512, 512-maskable, 180-apple-touch — all rendered from `favicon.svg` via `cairosvg`), `<link rel="manifest">` + `theme-color` + `apple-mobile-web-app-*` meta in base.html, mobile-only install card on the homepage that captures `beforeinstallprompt` (Android Chrome) and shows Share→Add-to-Home-Screen instructions (iOS Safari). Hides itself in `display-mode: standalone`
- [x] **Mobile quick-add page** (commits `c46376a`, `ca4823d`, `fada669`, `964f9bc`) — `/documents/<slug>/q/` (`wizard_quick_add` view) is the field-capture UI. Read-only chunk stack (parses `story_text` on `--- Added <stamp> ---` dividers via `_parse_story_chunks`) sits above a clearly-separated empty new-chunk textarea + voice mic, so cursor accidents in prior text are impossible. Pre-analyze: each save appends a timestamped chunk. Post-analyze: category picker + routes through `addendum_service` (non-destructive merge, preserves steps 1–7 edits). Dismissible "How this works" 3-step strip on first visit (localStorage-remembered). Dark-theme rules added so chunk text is readable in `[data-theme="dark"]`
- [x] **PWA `start_url` → active document** (commit `fada669`) — `/documents/start/` (`pwa_start` view) redirects to the user's most recent non-finalized document's `/q/` page; manifest `start_url` points there. Document list card promotes Quick add ("Add to story") to primary, demotes Continue + Edit story
- [x] **Per-chunk delete + dictation-duplication fix** (commit `95b4608`) — `withVoice` refuses to start when offline and tracks `_voiceLastIndex` to defend against misbehaving engines. New `/d/<slug>/q/delete-chunk/` endpoint with trash icons on every chunk card (saved chunks → server POST + confirm, queued chunks → IndexedDB delete)
- [x] **Step 7 case-law prompt prominence** (commit `98d19ea`) — amber alert styling + real CTA button when `caselaw_strategy='none'`; quiet review-card once a strategy is picked. Case law itself stays curated-fixture only (no AI, no web)
- [x] **`/guide/` user walkthrough** (commit `f456c93`) — 15-section single-page guide with sticky TOC, deliberately-long referral-program section because that's where a test user got stuck. Linked from navbar dropdown + footer
- [x] **"We're a Tool, Not Your Lawyer" homepage section** (commit `4e7e858`) — three-column cream-background disclosure between Quick Stats and Know-Your-Rights with links to Legal Disclaimer + User Guide
- [x] **`User.is_tester` flag for podcast-recruited testers** (`a3713a0`, migration `accounts/0006_user_is_tester`) — BooleanField + `tester_granted_at` auto-stamped by admin bulk action. UserAdmin column + filter + Tester Access fieldset + `mark_as_tester` / `revoke_tester` bulk actions. Story-page example-stories gate widened. Navbar shows yellow "Test mode" badge. Lower-privilege than `is_staff` — safe to grant unknown users
- [x] **Tester cleanup tooling** (`1232f98`) — `python manage.py seed_tester_promo` (creates / refreshes / `--deactivate`s a free-access PromoCode; default code `TESTFREE-<random6>`); third UserAdmin bulk action `reset_test_purchases` rolls paid+finalized docs back to draft, deletes matching PromoCodeUsage rows, decrements `PromoCode.times_used`
- [x] **Single-code tester signup** (`6a3aead`, migration `documents/0022_promocode_auto_grants_tester`) — `PromoCode.auto_grants_tester` BooleanField. Tester enters one code in the Referral Code field on `/accounts/register/`, gets both `is_tester=True` (autofill + badge) and the promo stashed in session for free `/pay/` checkout. `seed_tester_promo` defaults this to True on every code it seeds
- [x] **Offline PWA — app shell + outbox** (commit `99f76a0`) — Service worker at `/sw.js` (rendered from `templates/service-worker.js`; `Service-Worker-Allowed: /`) precaches theme CSS, manifest, all PNG/SVG icons, and `/documents/start/`, `/documents/`, `/accounts/login/`. Cache version = `RENDER_GIT_COMMIT[:8]` so every deploy invalidates. Fetch handler: network-first for navigation, cache-first for same-origin static; `/admin/`, `/api/`, `/stripe/`, `/sw.js` excluded. `wizard_quick_add` view returns JSON when `Accept: application/json` is set (`{ok, mode, chunk_number, timestamp}`). Page intercepts form submits — online → fetch POST + reload on success; offline / network failure → IndexedDB store `auditfile-outbox` keyed by `doc_slug`, queued cards render at top of stack with amber border, header shows Offline + N-queued badges. Drain runs on page load and `online` event (FIFO, stops on first failure to preserve order). Voice dictation still requires network (Web Speech API platform limit)
- [x] **Partner dashboard Phase 1 — foundation** (commit `f23dc7d`, accounts migration `0002`, documents migration `0018`) — `User.is_revenue_partner` BooleanField; `PayoutRequest` extended with `payment_processor` (PayPal/Venmo/Zelle/Check/Other), `payment_method_details` (where partner wants the money), `payment_reference` (admin-recorded txn ID/check #), `paid_at`, `admin_notes`. Admin form split into Request / Partner destination / Admin payment record fieldsets; auto-stamps `paid_at` and `resolved_at` when status changes. UserAdmin shows Partner column + filter
- [x] **Partner dashboard Phase 2 — read-only `/partner/`** (commit `bf06cf5`) — `documents/services/partner_stats.py` aggregates per-user sales, gross revenue, cut earned, paid out, pending, unpaid balance. Dashboard shows 4 summary cards + promo codes + recent sales (date, buyer name + email, code, amount, cut) + payout history. Nav link in user dropdown for partners + staff. Uses `PARTNER_CUT_PERCENT` setting
- [x] **Partner dashboard Phase 3 — payout request flow** (commit `f434e56`) — Bootstrap modal with payment-method dropdown + destination textarea + optional note. Settings: `PARTNER_MIN_PAYOUT_CENTS=2000` ($20 minimum), `PARTNER_PAYOUT_NOTIFY_EMAIL` env var (falls back to `DEFAULT_FROM_EMAIL`). View blocks if open request exists or unpaid balance < min. Button shows three states (live with amount / pending / below minimum). Email to admin includes deep link to admin record
- [x] **Partner dashboard Phase 4 — shareable `?ref=CODE`** (commit `9be59a2`) — `documents/middleware.py:CaptureReferralMiddleware` reads `?ref=` on every request, validates against `PromoCode` (active codes only, refuses to seed partner's own code), stores canonical-cased code in `session['referral_code']`. `/pay/` pre-fills the promo input + shows green "From referral link" badge + auto-validates on init. Latest valid `?ref=` clobbers older session value. Anonymous→authenticated session promotion preserves the captured code
- [x] **PartnerAdjustment model** (commit `2d281c6`, migration `0019`) — admin-created credit/debit on a partner's balance. Signed `amount_cents`, short visible `reason`, `created_by` auto-stamps with the admin user. Folds into `partner_stats.cut_cents`/balance; dashboard shows new Adjustments table with date / reason / signed dollar amount so partners see why their balance moved
- [x] **PartnershipRequest model** (commit `2d281c6`, migration `0019`) — non-partners see a "Request Partnership" form on profile (desired code + message). Submission creates a `PartnershipRequest` row + emails admin via `PARTNER_PAYOUT_NOTIFY_EMAIL`. Pending state replaces the form on subsequent profile views. **Approval auto-grants** (commit `3881a27`): when admin saves status=approved, `User.is_revenue_partner` flips to True AND a PromoCode is created using the requested code (or a unique fallback like `ALICE2` if taken / email prefix if blank), discount $50 fixed off, `created_by` = the user. Admin form description spells this out
- [x] **Profile page referral block** (commits `2d281c6`, `91f971c`) — replaces the old random `referral_code` display. Partners see active code(s) with copyable shareable link `https://{{ PRIMARY_DOMAIN }}/?ref=CODE` + button to open partner dashboard. Non-partners see Request Partnership form. Pending requests show a status banner. Page restructured: Profile col-lg-7 (left) + Referral col-lg-5 (right). Legacy "Access" card with `get_ai_uses_remaining` and "Upgrade (coming soon)" removed (replaced by per-document AI quota)
- [x] **PromoCode admin filter + relabel** (commits `43f131e`, `1386438`) — "Created by" dropdown filtered to `is_revenue_partner=True | is_staff=True` users only. Form label = "Assign code to"; list column = "Assigned to" (partner email)
- [x] **User admin: promo-codes-redeemed inline** (commit `2d281c6`) — read-only inline on User admin form showing every `PromoCodeUsage` where the user was the buyer, with referrer email + amount paid. Surfaces who-bought-using-whose-code at a glance
- [x] **Signup form referral pre-fill + two-tier referrer link** (commit `9b80225`) — register view seeds the input from `?ref=` query param or session value (set by middleware). Green "From referral link" badge appears when prefilled. `RegisterForm.save()` two-tier lookup: tries `User.referral_code` first (legacy random-string system), falls back to `PromoCode.code` and uses `created_by` as referrer. So `User.referred_by` now gets populated when a buyer signs up via a partner's link
- [x] **Canonical domain redirect** (commit `9d808c1`) — `documents/middleware.py:CanonicalDomainMiddleware` 301-redirects any host that isn't `PRIMARY_DOMAIN` to the same path on the canonical host. Skips localhost, IPs, `*.onrender.com`, and no-ops when `DEBUG=True`. `PRIMARY_DOMAIN='auditfile1983.com'` is the new default. Context processor exposes `{{ PRIMARY_DOMAIN }}` in templates so shareable links use it dynamically
- [x] **Email backend smart default** (commit `4e61d35`) — `EMAIL_BACKEND` now defaults to SMTP in production (DEBUG=False), console in dev. No env var needed in prod. Failure mode is "fail loudly with SMTP error" rather than "silently print bodies to logs"
- [x] **Password reset hardening** (commits `86e7c72`, `aa55041`, `2c966bb`) — `accounts/urls.py` namespaces `success_url` on `PasswordResetView`/`PasswordResetConfirmView` (was crashing post-send with `NoReverseMatch`). Custom `LogoutOnPasswordResetConfirmView` logs out the current session in dispatch so a logged-in user can't unknowingly reset a different account's password. Confirm template shows "Resetting password for `email@example.com`" banner. `LOGGING` config surfaces 500 tracebacks to stderr → Render logs. `EMAIL_TIMEOUT=15` so SMTP failures fail fast
- [x] **Finalize confirmation page + audit stamp** (commit `d8abdc8`, migration `0020`) — New URL `/documents/<slug>/finalize/` (`document_finalize` view) replaces the one-click JS `confirm()` with a dedicated checkbox confirmation page. POST requires the `acknowledge` checkbox; on success stamps `Document.finalize_acknowledged_at` AND `Document.locked_at` to the same `now` and flips `payment_status='finalized'`. The new `finalize_acknowledged_at` field is a separate audit timestamp (verifiable in admin) — admin changelist shows both columns; `DocumentAdmin.readonly_fields` includes `finalize_acknowledged_at`, `locked_at`, `paid_at`. The legacy `?finalize=1` query path on `wizard_generate` was removed. Same commit lifts `_check_locked_redirect()` to the top of every wizard view so locked docs block GETs too (previously only POSTs blocked) — `wizard_story`, `wizard_extraction_summary`, `wizard_addendum`, `wizard_step1`–`step7`, `wizard_caselaw_strategy`. The draft page itself stays open (re-download UI lives there)
- [x] **Watermark gated by lock, not payment** (commit `85f6d0e`) — `_build_complaint_context()` previously set `is_draft_preview = doc.payment_status != 'paid'`, which (a) let paid users hit `/wizard/generate/` for a clean PDF before locking and edit-preview-edit indefinitely, and (b) had a side bug where `payment_status='finalized'` re-watermarked. New rule: `is_draft_preview = not doc.is_locked()`. Only locked docs get a clean PDF; the only path to lock is `/finalize/`. The "Preview clean PDF" button on the draft page (paid+unlocked) was removed in favor of the watermarked Preview button, so paid users can still sanity-check layout before committing
- [x] **Brute-force login protection** (`django-axes`) — locks an account/IP out after repeated failed login attempts, with a cooloff timer before retrying. Required adding both `axes.backends.AxesBackend` (first) and `django.contrib.auth.backends.ModelBackend` to `AUTHENTICATION_BACKENDS` in `config/settings.py`, plus `axes.middleware.AxesMiddleware`. This multi-backend setup broke registration with a 500 (`AttributeError`/`ValueError`) because `django.contrib.auth.login()` couldn't infer which backend authenticated a freshly created user object — fixed by passing `backend='django.contrib.auth.backends.ModelBackend'` explicitly to `login()` in `accounts/views.py:register` (line ~43)
- [x] **IP throttling on registration / password reset** (`django-ratelimit`) — rate-limits submissions to `/accounts/register/` and the password-reset views by IP, independent of the per-account axes lockout, so a single IP can't hammer either endpoint
- [x] **Cookie + header hardening** — `SESSION_COOKIE_HTTPONLY`, `CSRF_COOKIE_HTTPONLY`, `SameSite=Lax` on both, plus standard production security headers (`SECURE_CONTENT_TYPE_NOSNIFF`, referrer policy) in `config/settings.py`
- [x] **Stale incident/government-entity data fix on re-analysis** — see GPT Extraction detail section above
- [x] **Per-document AI call cooldown** (`AICallTooSoon`) — see AI Quota + Document Locking detail section above
- [x] **Step 1 override now also exposes address re-entry** (commit `d016564`) — the "override the court" toggle previously only revealed the city/state/zip lookup inputs when no court had been auto-identified at all; if GPT had found a (wrong) court, overriding it dropped the user into a blind free-text court-name field with no way to correct the underlying address and re-run the lookup. Now overriding an already-identified court also reveals the same address fields, so a correction re-runs `CourtLookupService` instead of forcing a manual court guess

### Open
- [ ] **Landing page CMS** — `public_pages` is currently a stub. Now that `auditfile1983.com` is the primary domain, this is the homepage users land on
- [ ] Per-claim case law selection UI (Option B — let users curate which cases apply to which claims rather than auto-pick by amendment). Only worth building once we see whether users actually want curation; the auto-pick covers most auditor cases
- [ ] Playwright/Selenium browser tests for JS interactions (Alpine cards, timestamp spinner, draft textareas, voice button, addendum modal, payout-request modal, referral copy buttons)
- [ ] Switch Stripe to **Live mode** when ready to take real payments — generate live API keys, create a separate live webhook endpoint, update `STRIPE_*` env vars on Render. The code path is identical; only env vars change
- [ ] Drop stale `accounts.SiteSettings` price fields (`price_3pack`, `price_monthly`, `price_annual`) — not in any code path; remove in a future migration when convenient

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
  - **IncidentOverview and GovernmentEntity overwrite every field GPT returned, including blanking fields GPT now returns `null` for.** Previously `defaults` filtered out `None` values before calling `update_or_create`, and Django's `update_or_create(defaults=...)` leaves any key absent from `defaults` untouched on an existing row — so if a user edited their story and removed a detail (e.g. a street address), the old value silently stuck around through re-analysis. Fixed by mapping `None` → `''` for char/text fields instead of dropping the key. PlaintiffInfo intentionally still filters `None` (it's the user's own profile data, not story-derived, so GPT returning nothing for a field shouldn't ever erase it).
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

### County Lookup (`documents/services/county_lookup_service.py`)
- `CountyLookupService.lookup_county(city=None, state=None, zip_code=None)` — static-data-first, same philosophy as `CourtLookupService`: GPT's county guess from story text alone has no real data behind it, so it's only trusted as nothing — an unverifiable county renders blank, never a confident-looking fabrication.
- Two bundled datasets in `documents/services/county_data/`: `us_zip_county.json` (~33k ZIP→{county,state}, covers unincorporated places) checked first when a ZIP is available; `us_city_county.json` (~29.7k incorporated cities, MIT-licensed) as the city/state fallback. See `county_data/README.md` for full attribution.
- Used by `openai_service.extract_story()` (overrides GPT's county field) and `wizard_step1`'s GET-time auto-heal (fills county only when blank and a verified match exists — never overwrites a user's manual entry).

### Unverified Agency Heuristic (`documents/views._looks_like_unverified_agency`)
- Unlike courts (94 fixed federal districts) and counties (~3,143 fixed US counties), which agency policies a given small town isn't a clean lookup-table fact — no reliable free dataset exists, so this is a heuristic warning, not a static lookup.
- Returns True (unverified) when an `agency_name` doesn't contain the incident city name and doesn't already name `sheriff` / `state police` / `highway patrol` / `state patrol` / `county`, but does contain `police` or `department` — the generic-sounding pattern GPT tends to fabricate for small/rural towns instead of guessing the county sheriff or state police that more likely applies.
- Server-side: computed per-defendant in `wizard_step3` GET, passed as `unverified_agency` in the `defendants_json` context. Client-side: mirrored in `wizard_step3.html`'s Alpine `isUnverifiedAgency()` so the warning banner reacts live as the user edits the field. Banner text nudges the user to double-check (suggests searching "[officer]'s department") rather than guessing on the app's behalf.

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
- `0018_payoutrequest_processor_fields` — extends `PayoutRequest` with `payment_processor` (PayPal/Venmo/Zelle/Check/Other), `payment_method_details`, `payment_reference`, `paid_at`, `admin_notes`; reorders `notes` help text; adds `Meta.ordering = ['-requested_at']`
- `0019_partner_adjustment_partnership_request` — creates `PartnerAdjustment` (signed `amount_cents`, `reason`, `created_by`) and `PartnershipRequest` (`requested_code`, `message`, `status`, `admin_notes`, `resolved_at`)
- `0020_document_finalize_acknowledged_at` — adds `Document.finalize_acknowledged_at` (DateTimeField, null) — separate audit stamp from `locked_at` for the explicit checkbox acknowledgement on `/finalize/`
- `0021_document_download_disclaimer` — adds `Document.download_disclaimer_acknowledged_at` (DateTimeField, null) — stamped when user ticks the AI-disclaimer checkbox on `/finalize/` alongside the existing "complete" acknowledgement. Surfaced as readonly in DocumentAdmin.
- `0022_promocode_auto_grants_tester` — adds `PromoCode.auto_grants_tester` BooleanField — single-code tester signup (see Tester onboarding detail section)
- `0023_testerfeedback` — `TesterFeedback` model (free-text feedback capture + admin email)
- `0024_incidentoverview_zip_code` — adds `IncidentOverview.zip_code` (CharField, blank) — incident ZIP, used by `CountyLookupService` to verify county for unincorporated areas the city/state lookup misses
- `0025_alter_partneradjustment_id_and_more` — cosmetic migration-drift cleanup, auto-generated `verbose_name`/id-field alterations on `PartnerAdjustment` and related models picked up by `makemigrations` after a Django version bump; no behavior change

**accounts migrations:**
- `0001_initial` — User, Subscription, DocumentPack, SiteSettings, LegalDocument
- `0002_user_is_revenue_partner` — adds `User.is_revenue_partner` BooleanField (gates `/partner/` access)
- `0003_legal_acceptance` — adds `User.tos_accepted_at` / `tos_accepted_version` / `privacy_accepted_at` / `privacy_accepted_version`; adds `LegalDocument.version` (default `'v1'`) and `effective_date`; adds `'cookies'` to `LegalDocument.doc_type` choices; data migration seeds Terms + Privacy at version `'v1'` with disclaimer-heavy AI / not-a-lawyer copy
- `0004_rebrand_legal_copy` — rebrands seeded Terms + Privacy from "File 1983" → "AuditFile 1983"; adds "Who we are" section defining "AuditFile 1983 Parties" (owners, officers, members, employees, contractors, agents, representatives, affiliates, successors); references that defined term in limitation-of-liability + indemnification clauses; nudges `SiteSettings.app_name` + `header_app_name` to "AuditFile 1983" if still on the original default; uses `update_or_create` so it works whether or not 0003 already ran
- `0005_sitesettings_contact` — adds `SiteSettings.contact_email` (default `rights@auditfile1983.com`), `contact_email_visible`, `contact_phone` (default `555-555-1212`), `contact_phone_visible` for the footer
- `0006_user_is_tester` — adds `User.is_tester` BooleanField + `tester_granted_at` timestamp (see Tester onboarding detail section)

**public_pages migrations:**
- `0001_initial` — `CivilRightsPage`, `PageSection` (CMS scaffolding)
- `0002_newsitem` — adds `NewsItem` (url unique, title, source, published_at, summary, is_visible, fetched_at) for the landing-page RSS widget

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

### Tester onboarding (`User.is_tester`)
- `User.is_tester` (BooleanField, default False) + `User.tester_granted_at` (auto-stamped by the admin bulk action). Migration `accounts/0006_user_is_tester`.
- **Why this exists:** the developer is recruiting unknown podcast volunteers to test the app. Making them `is_staff` would unlock `/manage-dev/` and document-delete buttons — too risky. `is_tester` is a lower-privilege flag that today only unlocks the example-stories autofill on the wizard story page, and shows a yellow "Test mode" badge in the navbar so the tester knows they're in test mode and the developer can spot test accounts in screenshots.
- **Granting / revoking:** UserAdmin list view has two bulk actions (`mark_as_tester` / `revoke_tester`) — check the rows, pick the action, hit Go. The "Tester Access" fieldset on the user detail page also has a single checkbox + the read-only `tester_granted_at` timestamp.
- **Gate widening:** any future tester-only feature should gate on `request.user.is_staff or request.user.is_tester or settings.DEBUG`. Today that pattern only lives in `wizard_story` view's example-stories block.
- **Walkthrough script for the developer to use while screen-sharing with each tester:** kept in chat history of the session that built this; ~50 numbered steps across signup → profile → wizard → draft → payment → finalize → mobile PWA install → quick-add → offline → password reset → (optional) partner referral. Stripe test card `4242 4242 4242 4242` with any future expiry / any CVC / any ZIP.
- **Free-access promo code for testers (single-code unified flow):** new management command `python manage.py seed_tester_promo` (in `documents/management/commands/`). Creates (or refreshes) a `PromoCode` with `discount_type='free'`, `is_active=True`, **and `auto_grants_tester=True`**. Defaults the code to `TESTFREE-<random6>` so it can't be guessed by random visitors; override with `--code MYCODE`. Run with `--deactivate --code MYCODE` to flip `is_active=False` when the round ends.
- **`PromoCode.auto_grants_tester`** (`documents/0022_promocode_auto_grants_tester`) — when True, anyone who enters the code in the **Referral Code field on `/accounts/register/`** is auto-marked `is_tester=True` + `tester_granted_at=now()`, AND the canonical code is stashed in `request.session['referral_code']` so it pre-fills at `/pay/` checkout. So testers enter the code in **one place** (signup) and get both ends — example-stories autofill + "Test mode" badge + free Stripe Checkout — without any manual admin step. Logic lives in `RegisterForm.save()` (sets the flag and `_granted_tester_code`) and `accounts.views.register` (stashes the code in session + tweaks the welcome message). Re-uses the existing dual-purpose Referral Code field — partner referral lookup and tester-grant lookup are both done from the same input, with no collision because `_resolve_referrer` only sets `referred_by` when the promo has a `created_by` (the seeded tester promos don't).
- **Cleanup after a testing round** — a third UserAdmin bulk action: **"Reset test purchases (paid + finalized) on selected users to draft"** (`reset_test_purchases`). For every paid/finalized document owned by the selected users, it: rolls `payment_status` back to `'draft'`; clears `paid_at`, `stripe_session_id`, `locked_at`, `finalize_acknowledged_at`, `download_disclaimer_acknowledged_at`; deletes the matching `PromoCodeUsage` rows; decrements `PromoCode.times_used` by the corresponding count. Documents themselves are preserved so you can inspect the wizard data. **Typical end-of-round workflow:** select testers → "Reset test purchases" → "Revoke tester status" → run `seed_tester_promo --deactivate --code TESTFREE-XXX`.
- **`python manage.py revoke_testers`** — management-command equivalent of the "Revoke tester status" bulk action, for strip `is_tester` from *every* account at once (rather than selecting rows in admin one by one). Useful as the last step of an end-of-round cleanup when there are too many testers to comfortably multi-select in the admin list view. Pair with `seed_tester_promo --deactivate` to also retire the code.

### Mobile / PWA (`wizard_quick_add`, `pwa_start`, `service_worker`)
- **`/documents/<slug>/q/`** (`documents/views.py:wizard_quick_add`) is the field-capture page. Dual semantics keyed off `session.ai_extraction_succeeded`:
  - **Before analyze:** appends each chunk to `WizardSession.story_text` with `--- Added <Mon D, YYYY H:MM PM UTC> ---` divider. `_parse_story_chunks` splits on that pattern at render time so the template shows each chunk as its own card with `#N` badge and timestamp. Text before the first divider (legacy single-textarea content) appears as an "Original story" intro card with a navy left border.
  - **After analyze:** shows a category picker and routes the POST through `documents.services.addendum_service.apply_addendum` (the same path the wizard summary's "Add details" buttons use). Manual edits in steps 1–7 are preserved by the non-destructive merge.
- POST accepts `Accept: application/json` and returns `{ok, mode, chunk_number, timestamp}` (or `{ok: false, error}`) — used by the page's IndexedDB outbox to replay queued saves.
- **`/documents/start/`** (`documents/views.py:pwa_start`) — the PWA `start_url` target. Picks the user's most recent non-finalized `Document` and 302s to its `/q/` page. Falls back to `/documents/` when there are none. Auditor taps home-screen icon → lands on the field input.
- **Document list card** (`templates/documents/list.html`) makes "Add to story" the primary button on any open doc with story content. Continue drops to outlined secondary, Edit story to a muted text link.
- **Manifest** at `static/manifest.webmanifest` — `start_url=/documents/start/`, `display=standalone`, `theme_color=#002868`, icons reference `/static/images/pwa/icon-{192,512,512-maskable}.png` first, SVG as a fallback. `<link rel="manifest">`, `theme-color`, `apple-mobile-web-app-*` meta, and `apple-touch-icon` are wired in `templates/base.html`.
- **Icons** generated from `static/images/favicon.svg` via `cairosvg`. To regenerate run the one-shot script at `/tmp/render_pwa_icons.py` (kept out of the repo — recreate from the commit `b224a2d` message if you need it). Maskable variant drops the rounded-corner rect and insets the gavel into the 80% safe zone so Android can crop to any mask shape without losing the icon.
- **Mobile install card** on the homepage (`templates/public_pages/landing.html`, `d-lg-none`) — gradient card under the hero. Captures `beforeinstallprompt` via a global handler in `base.html` (`window.__deferredInstallPrompt`), exposes a tap-to-install button on Android Chrome, falls back to inline Share→Add-to-Home-Screen instructions on iOS. Hides itself when `display-mode: standalone` (already installed).
- **Service worker** at `/sw.js` — source is the Django template `templates/service-worker.js`, rendered by `documents.views.service_worker` with `cache_version` baked in (uses `RENDER_GIT_COMMIT[:8]` env var on Render, falls back to process-start timestamp). Header `Service-Worker-Allowed: /` lets it claim the whole origin from a non-root URL. Strategy:
  - **App shell precached** on install: theme CSS, manifest, all PNG/SVG icons, `/documents/start/`, `/documents/`, `/accounts/login/`. Best-effort `addAll` (per-URL `cache.add().catch(null)`) so one 404 doesn't break install.
  - **Fetch handler:** network-first for navigation (live data stays fresh, cached as fallback). Cache-first for same-origin static assets. `/admin/`, `/api/`, `/stripe/`, `/sw.js` itself, and any non-GET request pass through unmodified.
  - Registered from `base.html` on `window.load` — wrapped in `'serviceWorker' in navigator` so old browsers no-op.
- **IndexedDB outbox** — DB `auditfile-outbox`, store `chunks` (autoIncrement `id` keypath, indexed on `doc_slug`). Records: `{doc_slug, text, category?, created_at}`. Helpers live inline at the top of `templates/documents/wizard_quick_add.html` (exposed as `window.__outbox`). The Alpine component on the page wires the form: online attempt → `fetch` POST with `Accept: application/json`; on network failure (or `!navigator.onLine`) → `__outbox.add()`, refresh `queuedItems`, clear input. Queued cards render at the top of the chunk stack with amber border. Drain runs in `init()` (after queue load) and on the browser's `online` event — FIFO, stops on first failure to preserve order, reloads the page on any successful drain so queued cards become saved chunks.
- **CSRF caveat:** the cached HTML carries the CSRF token from its original render. As long as the session cookie is still valid (Django default 2 weeks) the token validates on replay. Re-logging in between offline-save and online-sync would invalidate the token; the queued chunk would then fail to POST and stay in the outbox. No retry-with-fresh-token logic today — call this out if it shows up in testing.
- **Voice dictation does NOT work offline.** Web Speech API on Android Chrome uses Google's cloud STT; iOS Safari is inconsistent. Service worker can't fix this. Typing offline works.

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
- **Document locking** — `Document.locked_at` (DateTime null=True); `Document.is_locked()` helper. Set by the new `/documents/<slug>/finalize/` confirmation page (`document_finalize` view) — POST stamps `locked_at` AND `finalize_acknowledged_at` together, flips `payment_status='finalized'`, then redirects to `wizard_generate?download=1`. Replaces the old one-click `wizard_generate?finalize=1&download=1` JS-confirm path.
- **Lock-blocking** — `_check_locked_redirect()` helper returns a redirect to `wizard_draft` with a flash if the doc is locked; called at the **top** of every wizard view (both GET and POST): `wizard_story`, `wizard_extraction_summary`, `wizard_addendum`, `wizard_step1`–`step7`, `wizard_caselaw_strategy`, `wizard_draft` (POST only — GET stays open since the re-download UI lives there), `wizard_draft_undo`. Lock is per-document; other documents in the same account stay editable. Locked-state UI on draft page: banner + Save/Re-draft buttons hidden + "Re-download PDF" replaces "Finalize & Download". Lock icon on Finalized status badge in documents list.
- **Watermark gating** — `_build_complaint_context()` sets `is_draft_preview = not doc.is_locked()`. Paid-but-unlocked previews are still watermarked, so a paid user can't grab a clean PDF without going through `/finalize/`. After lock, all `wizard_generate` calls (including `?download=1` re-downloads) render clean.
- **Per-document AI call cooldown** (`AI_CALL_COOLDOWN_SECONDS`, default 8s) — a second, independent guardrail from the quota above. The quota caps *total* calls; the cooldown caps the *rate* of calls, so mashing Analyze/Re-draft/Add repeatedly can't fire several real OpenAI calls (and burn quota or cost) within a couple seconds. Implemented with `django.core.cache.cache` — `consume_ai_call()` sets a `ai-call-cooldown:<pk>` cache key for `AI_CALL_COOLDOWN_SECONDS` after every successful call; a call attempted while that key is still set raises `AICallTooSoon` instead of `QuotaExceeded` (so it doesn't burn quota). `can_use_ai()` also checks the cooldown for quick pre-flight checks. Caveat: LocMemCache is per-process, not multi-worker-safe — fine for the current single-worker Render setup, would need a shared cache (e.g. Redis) if Render is ever scaled to multiple gunicorn workers.
- **Cooldown UX** — All 5 call sites (`wizard_story` analyze, `wizard_addendum`, `wizard_quick_add` post-analyze addendum, `wizard_draft` regenerate, `wizard_draft` GET-time auto-generate) catch `AICallTooSoon` before `QuotaExceeded` and flash a "please wait a few seconds" warning via `messages.warning()`, rendered through the standard `{% if messages %}` Bootstrap alert block already on every wizard page (confirmed on `wizard_draft.html`). The JSON-response path in `wizard_quick_add` (used by the offline-outbox fetch flow) returns `{'ok': False, 'cooldown': True}` with HTTP 429 instead of a redirect.

### Finalize Confirmation Flow (`documents/views.py:document_finalize`)
- **Goal:** require an explicit, audit-stamped acknowledgement before locking a paid document and serving the clean PDF. Replaces the older one-click JS `confirm()` flow.
- **URL:** `/documents/<slug>/finalize/` (named `documents:document_finalize`).
- **GET** → renders `templates/documents/finalize_confirm.html`: warning panel + required checkbox ("I confirm this complaint is complete and I understand that submitting will permanently lock editing on this document. The PDF will remain available to re-download.") + Cancel / Confirm & Download buttons.
- **POST** → requires `acknowledge` checkbox; if missing, re-renders with an error flash. On success, sets `Document.finalize_acknowledged_at = now`, `Document.locked_at = now`, `payment_status='finalized'` (single `save(update_fields=...)`), then redirects to `wizard_generate?download=1` so the browser save dialog fires.
- **Guards:** already-locked → bounces to draft (info flash). Unpaid → bounces to `/pay/` (warning flash). No paragraphs → bounces to draft (warning flash).
- **Audit:** `finalize_acknowledged_at` is a separate field from `locked_at` (even though both are stamped at the same `now`) so the explicit user acknowledgement is independently verifiable. `DocumentAdmin` shows both in the changelist + as readonly fields. `paid_at` is also readonly so admin can correlate the three timestamps.
- **Watermark interaction:** `_build_complaint_context()` keys the watermark off `doc.is_locked()`, so the redirect to `wizard_generate?download=1` after this view's POST is the first time the user gets a clean PDF. Pre-finalize, even paid users only see the watermarked preview.

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

### Partner Dashboard (`/partner/`)
- **Access gating** — `documents/views.py:_is_partner` allows `is_revenue_partner OR is_staff`. View at `/partner/` renders `templates/partner/dashboard.html`.
- **Stats helper** — `documents/services/partner_stats.py:get_partner_stats(user)` returns a dict with: `cut_percent`, `codes` (queryset), `sales_count`, `gross_cents/dollars`, `cut_cents/dollars` (sales cut + adjustments), `paid_out_cents/dollars`, `pending_cents/dollars`, `unpaid_balance_cents/dollars`, `recent_sales` (list of dicts with `used_at`, `buyer_name`, `buyer_email`, `code`, `amount_dollars`, `cut_dollars`), `payouts` (queryset), `has_open_request`, `adjustments` (list with precomputed `amount_display`), `sales_cut_*`, `adjustments_*`.
- **Adjustments fold in** — `cut_cents = sales_cut_cents + adjustments_cents`, so a `PartnerAdjustment(+500)` bumps the unpaid balance by $5; a `PartnerAdjustment(-1000)` clawbacks $10. Dashboard shows the adjustments table only when there are rows (date / reason / signed `+$X.XX` or `-$X.XX`).
- **Payout request modal** — Bootstrap modal with `payment_processor` select, `payment_method_details` textarea (PayPal email, Venmo handle, Zelle phone/email, mailing address for check), optional `notes`. Posts to `/partner/request-payout/`.
- **Min balance + open-request guard** — `PARTNER_MIN_PAYOUT_CENTS=2000`. Below that the button is disabled with a tooltip. While a `pending`/`approved` PayoutRequest exists for the user, the button shows "Request pending" disabled.
- **Admin email** — `partner_request_payout` calls `send_mail(subject="[file1983] Payout request: $X from email", to=PARTNER_PAYOUT_NOTIFY_EMAIL, fail_silently=True)` with partner info + deep link to the admin record. Same pattern in `accounts/views.py:request_partnership` for partnership requests.

### Partnership Request Flow (self-serve onboarding)
- **Profile form** (`templates/accounts/profile.html`) — non-partners see a "Request Partnership" form: desired code (`pattern="[A-Za-z0-9_-]+"`, max 30 chars) + optional message. Pending state replaces the form on next view.
- **Submission** — `accounts/views.py:request_partnership` (POST-only). Blocks duplicate pending requests. Creates a `PartnershipRequest`, emails admin.
- **Auto-grant on approval** — `documents/admin.py:PartnershipRequestAdmin.save_model` calls `_grant_partnership(request, obj)` when status=approved:
  - Sets `user.is_revenue_partner = True` if not already
  - Calls `_unique_promo_code(requested, user)` to find a free code: tries the requested code, falls back to `REQUESTED2`, `REQUESTED3`, ... up to 100; if `requested` is empty, falls back to email prefix uppercased
  - Creates `PromoCode(code=found, discount_type='fixed', discount_value=50, is_active=True, created_by=user)` — $50 off matches the $99 discounted price
  - Skips creation if the user already has an active code (admin-friendly message)
- **Manual override** — admin can still flip `User.is_revenue_partner` and create the PromoCode by hand in admin if they want a different code or different discount type.

### Canonical Domain Redirect (`PRIMARY_DOMAIN`)
- **Setting** — `PRIMARY_DOMAIN = config('PRIMARY_DOMAIN', default='auditfile1983.com')` in `config/settings.py`.
- **Middleware** — `documents/middleware.py:CanonicalDomainMiddleware` runs on every request. Skips when `DEBUG=True`. Skips localhost / IPs / `*.onrender.com`. For any other host that isn't `PRIMARY_DOMAIN`, returns a 301 redirect to `https://{PRIMARY_DOMAIN}{request.get_full_path()}`. `www.<canonical>` also redirects to bare canonical.
- **Template access** — `config/context_processors.py:site_settings` injects `PRIMARY_DOMAIN` into every template. Used by the profile-page shareable referral link: `https://{{ PRIMARY_DOMAIN }}/?ref={{ code.code }}`.
- **To swap canonical** — set Render env var `PRIMARY_DOMAIN=file1983.com` (or whatever) and Render auto-redeploys. No code or DNS change needed.

### Referral Capture Middleware (`?ref=CODE`)
- **`documents/middleware.py:CaptureReferralMiddleware`** — runs on every request. When `request.GET.get('ref')` is set:
  - Looks up `PromoCode.objects.filter(code__iexact=ref, is_active=True).first()`
  - If found AND not the requesting user's own code, stores the canonical-cased code in `request.session['referral_code']`
  - Latest valid `?ref=` clobbers any older session value
  - Invalid / inactive codes are silently ignored — no garbage in session
- **Pre-fill at checkout** — `payment_start` view reads `request.session.get('referral_code')` and passes as `prefilled_code` to `templates/documents/payment_start.html`. The Alpine `paymentForm` seeds `code` from `prefilledCode` and `init()` triggers `checkCode()` so the discounted price renders without typing.
- **Pre-fill at signup** — `accounts/views.py:register` reads `?ref=` directly OR `session['referral_code']` and passes as initial value to `RegisterForm`. Template shows a green "From referral link" badge.
- **Linking referrer at signup** — `RegisterForm.save()._resolve_referrer()` does a two-tier lookup: first `User.referral_code` (legacy random string), then falls back to `PromoCode.code` and uses `created_by` as the referrer. Sets `User.referred_by` so admin can see who referred whom.

### Password Reset Flow
- **URL config** — `accounts/urls.py` namespaces `success_url=reverse_lazy('accounts:password_reset_done')` and `accounts:password_reset_complete`. (Without explicit `success_url`, Django's default `reverse_lazy('password_reset_done')` returns NoReverseMatch because of `app_name='accounts'`.)
- **Templates** — `password_reset.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html` in `templates/accounts/`. Email body templates: `templates/accounts/emails/password_reset_email.txt`, `password_reset_subject.txt`.
- **`LogoutOnPasswordResetConfirmView`** (in `accounts/views.py`) — subclass of Django's `PasswordResetConfirmView` that logs out the current session in `dispatch()`. Avoids the confusion of a logged-in user resetting a different account.
- **Target-email banner** — `password_reset_confirm.html` shows `Resetting password for {{ form.user.email }}` so users see exactly which account is being changed.
- **Email backend** — `EMAIL_BACKEND` auto-defaults to SMTP when `DEBUG=False`, console when `DEBUG=True`. Means prod sends real email without an env var; dev prints to console without configuration. SMTP via Namecheap Private Email at `mail.privateemail.com:587` STARTTLS, login `rights@auditfile1983.com`.
- **Logging** — `LOGGING` in `config/settings.py` routes `django.request` ERROR-level logs (and `django` INFO) to stderr so 500 tracebacks appear in Render logs.

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

> **Heads-up on app placement:** `PromoCode`, `PromoCodeUsage`, `PayoutRequest`, `PartnerAdjustment`, `PartnershipRequest` all live in **`documents/models.py`** (not `accounts/`). The `accounts` app only has `User`, `Subscription`, `DocumentPack`, `SiteSettings`, `LegalDocument`. Earlier drafts of this doc said `accounts.PromoCode` / `accounts.PayoutRequest` — those were wrong.

**Shipped:** pricing model, Stripe Checkout (Phases 2 + 3), Stripe Phase 4 (finalize + lock on download), per-document AI quota, document locking, **full partner dashboard (Phases 1–4)**, partnership self-request + auto-grant on approval, balance adjustments, canonical-domain redirect, password-reset SMTP+UX hardening. See **Build Status → Done** and **What's Built — Detail** for commit SHAs and full shape.

**Decided knobs:**
- Referrer cut is **20% of $99 = $19.80 per sale** (`settings.PARTNER_CUT_PERCENT=20`)
- Min payout balance: $20 (`settings.PARTNER_MIN_PAYOUT_CENTS=2000`)
- Partners see buyer name + email on sales rows (transparency)
- CSV export is admin-only (no partner-side export)
- Auto-granted PromoCode for approved partners: `discount_type='fixed', discount_value=50` ($149 → $99)

**Stale schema cleanup:** unused `price_3pack` / `price_monthly` / `price_annual` fields on `accounts.SiteSettings` are not in any code path. Safe to drop in a future migration when convenient.

### Open
- **Landing page CMS** — `public_pages.CivilRightsPage` + `PageSection` models already exist with the right shape. Just need admin polish (a couple of seeded section types, maybe a preview button) and a few seeded pages.
- **Stripe Live mode** — generate live API keys in Stripe, create live webhook endpoint pointed at `https://auditfile1983.com/stripe/webhook/` with events `checkout.session.completed` + `checkout.session.expired`, update `STRIPE_SECRET_KEY` / `STRIPE_PUBLISHABLE_KEY` / `STRIPE_WEBHOOK_SECRET` env vars on Render. The code path is identical; only env vars change. **Caveat:** test-mode `PromoCode` and `PromoCodeUsage` rows are still in the DB — audit before going live so test partners don't accidentally get real attribution.
- **Capacitor native wrapper** (deferred — only if a real demand surfaces). The site already ships as an installable PWA so most "feels native" wins are covered. A Capacitor build would add app-store distribution + real push notifications + the option to swap in a native Speech-to-Text plugin (iOS Speech framework) to fix the voice-offline limit. Costs: $25 one-time Play developer fee, $99/yr Apple Developer Program, Mac (or cloud Mac) for iOS builds, ongoing native-build maintenance. Two shapes if the user wants this: (a) thin shell that loads `https://auditfile1983.com` in a WebView (fast, but barely better than the PWA), (b) split off a static/SPA frontend that Capacitor bundles + Django serves JSON (real native feel but a wizard rewrite — not worth it for this user). Recommend (a) when the time comes, plus a native STT plugin for the dictation page.
- Per-claim case-law selection UI (Option B)
- Playwright/Selenium browser tests
- Drop unused `price_3pack` / `price_monthly` / `price_annual` fields on `accounts.SiteSettings` when convenient
- **Quick-add CSRF refresh on outbox replay** — today the queued POST uses whatever CSRF token was in the cached HTML when the user went offline. Valid for the session lifetime (~2 weeks default). If the user logs out and back in between offline-save and online-sync, the token is invalidated and the queued chunk silently fails to POST (stays in the outbox). A small follow-up would be: when drain hits a 403, fetch a fresh CSRF token (e.g. via a `/csrf/` endpoint or by reading the `csrftoken` cookie directly) and retry once. Not urgent — the realistic offline window is minutes to hours, not days
- **Quick-add full-text edit** — `/q/` deliberately only appends; the cards above the input are read-only so users can't accidentally inject mid-stream dictation. To edit a typo in an earlier chunk users currently go to `/wizard/` (Edit story). A future polish would be inline "Edit" on a chunk card that rewrites the `--- Added ... ---` block in `story_text`. Defer until a user actually asks for it

### Working agreement
User wants to take features one at a time, structured. Don't bundle. Run the deploy + test loop after each meaningful commit before moving on.

The user's `/q/` page now feeds chunks into the same `story_text` field the wizard's Analyze step reads from. If you change the chunk divider format (`--- Added <stamp> ---`) anywhere, update `_parse_story_chunks` in `documents/views.py` to match, and confirm the GPT extraction prompt still handles the dividers cleanly (it does today — they're treated as narrative context).

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
