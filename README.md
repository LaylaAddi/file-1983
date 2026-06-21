# AuditFile 1983

A Django web app that walks someone through building a **Section 1983 federal civil
rights complaint** — the kind of lawsuit filed against police officers or other
government officials for violating someone's constitutional rights (wrongful arrest,
excessive force, retaliation for filming in public, etc).

Target users: First Amendment auditors, people who've had a bad interaction with
police, and anyone who wants to put their story into a properly-formatted federal
complaint without hiring a lawyer first. **It is not a law firm and the output is not
legal advice** — the app is explicit about this everywhere (signup, footer, finalize
page) and recommends consulting a real attorney when in doubt.

Live at **auditfile1983.com**.

---

## The 60-second version

1. User signs up, fills in their address/contact info once on their profile.
2. User tells their story in plain English (typed, dictated by voice, or added in
   small pieces over time from their phone).
3. GPT-4o reads the story and extracts structured facts: who, what, where, when,
   which officers, what evidence exists, what constitutional claims apply.
4. A 7-step wizard lets the user review and correct everything GPT found —
   jurisdiction, incident details, defendants, claims, evidence/witnesses, damages —
   nothing gets filed without the user seeing and confirming it.
5. The user picks whether to cite supporting case law (optional).
6. GPT drafts the "factual allegations" — the actual narrative paragraphs of the
   complaint — in the user's own first-person voice. The user can edit or
   regenerate it.
7. A full federal-court-formatted PDF is generated (via WeasyPrint). Free preview is
   watermarked "DRAFT — NOT FOR FILING"; paying removes the watermark.
8. Once the user is done, they explicitly confirm and "finalize" the document, which
   locks editing and unlocks a clean PDF they can re-download anytime.

---

## Tech stack

| Layer | Choice |
|---|---|
| Backend | Django 4.2 (Python 3.12) |
| Database | PostgreSQL (SQLite fine for local dev) |
| Frontend | Server-rendered Django templates + Bootstrap 5.3 + Alpine.js for interactivity |
| AI | OpenAI GPT-4o — story extraction, draft writing, court-lookup fallback |
| Payments | Stripe Checkout |
| PDF | WeasyPrint (HTML/CSS → PDF, federal court formatting) |
| Auth | Custom email-based `User` model (no usernames); `django-axes` for login lockout, `django-ratelimit` for IP throttling |
| API | Django REST Framework + SimpleJWT (exposed, not used by the web UI today) |
| Deploy | Docker container on Render, auto-deploys from `master` |
| PWA | Installable on mobile (manifest + service worker), offline-capable story capture |

---

## Repository layout

```
config/             Django project settings, root URLs, WSGI/ASGI
accounts/           User model, auth views (login/register/password reset), profile,
                     partner/legal-acceptance plumbing
documents/           The actual product: the wizard, all case-data models, AI
                     services, Stripe integration, PDF generation, admin
public_pages/       Marketing/landing site (home, legal pages, user guide, CMS stub)
templates/          All HTML templates, organized by app + a shared base.html
static/             CSS, images, PWA icons/manifest
documents/services/ Business logic that isn't a Django view — see below
documents/fixtures/ Seed data — example stories, foundational case law
```

### `documents/services/` — where the real logic lives

| File | What it does |
|---|---|
| `openai_service.py` | Calls GPT-4o to turn the user's free-text story into structured JSON, then writes that JSON into all the wizard models (`_populate_models`). Also has the amendment/state normalization helpers. |
| `complaint_drafter.py` | Turns the story + structured data into numbered, first-person "factual allegations" paragraphs — the narrative heart of the complaint. |
| `caselaw_picker.py` | Auto-selects supporting case law (from a small curated, fixture-seeded library — not a live legal database) based on which constitutional amendments are in play. |
| `court_lookup_service.py` | Maps an incident city/state to the correct federal district court — static data first, GPT as a last-resort fallback. |
| `county_lookup_service.py` | Same idea for county — static ZIP/city datasets first; never lets GPT's unverifiable guess show up as if it were confident. |
| `addendum_service.py` | Lets a user add more detail to one category (e.g. "more about evidence") *after* the initial extraction, without re-running the whole pipeline and clobbering their manual edits. |
| `stripe_service.py` | Builds Stripe Checkout Sessions, validates promo codes against our own `PromoCode` table (not Stripe Coupons). |
| `ai_quota.py` | Enforces a per-document cap on AI calls (so one document can't run up unlimited OpenAI spend) *and* a short per-document cooldown so a user mashing a button repeatedly can't fire calls faster than the cooldown window. |
| `partner_stats.py` | Aggregates a referral partner's sales, commission, and payout balance for their dashboard. |

---

## The wizard flow, end to end

```
/documents/new/                 → create a Document + WizardSession + PlaintiffInfo
/documents/<slug>/wizard/       → tell your story (type, dictate, or paste)
   ↓ POST "Analyze" → GPT extracts structured facts → models populated
/documents/<slug>/wizard/summary/   → "here's what we found / what's missing"
/documents/<slug>/wizard/step1/     → confirm federal jurisdiction (which court)
/documents/<slug>/wizard/step2/     → incident details (when, where, what happened)
/documents/<slug>/wizard/step3/     → who's being sued (defendants + government entity)
/documents/<slug>/wizard/step4/     → which constitutional rights were violated
/documents/<slug>/wizard/step5/     → evidence & witnesses
/documents/<slug>/wizard/step6/     → damages & what relief you're asking for
/documents/<slug>/wizard/step7/     → final review, jump back to fix anything
/documents/<slug>/wizard/caselaw/   → optional: cite supporting case law
/documents/<slug>/wizard/draft/     → AI writes the narrative, user edits/regenerates
/documents/<slug>/pay/              → Stripe Checkout ($149, or $99 with a promo code)
/documents/<slug>/finalize/         → explicit two-checkbox confirmation, locks the doc
/documents/<slug>/wizard/generate/  → the actual PDF (watermarked until finalized)
```

A user can also add to their story incrementally from their phone at
`/documents/<slug>/q/` ("quick add") — handy for jotting things down right after an
incident instead of writing the whole story at once. Before the first AI analysis
each entry just appends to the story; after analysis, entries route through the
addendum service so they merge into the right wizard section without overwriting
manual edits.

---

## Data model, in plain English

Each **Document** belongs to one user and owns everything else (one-to-one or
foreign-keyed): `PlaintiffInfo` (who's filing), `IncidentOverview` (what/where/when),
`TimelineEntry` rows (chronological events), `Defendant` rows (who's being sued),
`GovernmentEntity` (for municipal-liability / *Monell* claims), `ConstitutionalClaim`
rows (which amendments), `Evidence` and `Witness` rows, `Damages`, `ReliefSought`,
`PriorComplaints`, and a `WizardSession` that tracks the raw story text and how far
through the wizard the user has gotten.

Payment/lifecycle state lives directly on `Document`: `payment_status` (draft → paid
→ finalized), `ai_calls_used` (quota), `locked_at` (set once finalized — nothing on a
locked document can be edited again), and cached AI output
(`factual_allegations_json`, with a one-level undo snapshot).

Money/referrals: `PromoCode` (discount codes, also doubles as the free-access
mechanism for test users), `PromoCodeUsage` (audit trail of who used what code),
`PartnerAdjustment` and `PayoutRequest` (manual balance corrections and payout asks
for revenue-sharing partners), `PartnershipRequest` (self-serve "make me a partner"
applications that an admin approves).

---

## AI usage controls

Two independent guardrails keep OpenAI usage bounded and protect against abuse:

- **Quota** (`AI_QUOTA_FREE` / `AI_QUOTA_PAID`, default 3 / 150) — a hard cap on total
  AI calls per document. Resets to a fresh budget once the document is paid for.
- **Cooldown** (`AI_CALL_COOLDOWN_SECONDS`, default 8) — a short per-document
  cooldown so repeatedly clicking "Analyze" / "Re-draft" / "Add details" can't fire
  several real API calls in a couple of seconds. The user sees a "please wait a
  moment" message instead of the call silently going through or quota draining fast.

Story extraction always re-derives every field from the current story text — if a
re-analyzed story no longer mentions a street address, that field is cleared rather
than left showing data from a previous version of the story.

---

## Security

- Custom email-based auth (no usernames).
- `django-axes` locks an account/IP out after repeated failed logins (cooloff timer).
- `django-ratelimit` throttles registration and password-reset submissions by IP.
- Hardened cookies (`HttpOnly`, `SameSite=Lax`) and standard security headers
  (`X-Content-Type-Options`, referrer policy) in production.
- Every document view checks ownership (`Document.objects.get(slug=..., user=request.user)`)
  — there's no way to view or edit someone else's document by guessing a slug.
- Terms of Service / Privacy Policy acceptance is required at signup and re-required
  (via middleware) whenever the legal copy version changes.
- Stripe webhook payloads are signature-verified before any state changes.

---

## Local development

```bash
docker compose build web        # only needed when Dockerfile/requirements change
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata example_stories
docker compose exec web python manage.py loaddata foundational_case_law
docker compose exec web python manage.py createsuperuser
```

Copy `.env.example` (or see **Environment variables** below) into a `.env` file
before bringing the containers up — at minimum you'll want `OPENAI_API_KEY` set, or
the wizard's Analyze step will fail.

Run the test suite:

```bash
docker compose exec web python manage.py test documents -v 2
```

### Environment variables

```
SECRET_KEY=
DEBUG=1                          # 0 in production
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgresql://postgres:postgres@db:5432/file1983
ADMIN_URL=manage-dev/            # path to the Django admin, kept non-obvious in prod

OPENAI_API_KEY=                  # required for story extraction, drafting, court-lookup fallback

STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=

EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=

PRIMARY_DOMAIN=auditfile1983.com   # canonical host; other hosts 301-redirect here
PARTNER_PAYOUT_NOTIFY_EMAIL=       # where partnership/payout request emails go (defaults to DEFAULT_FROM_EMAIL)
```

In production, email automatically uses real SMTP; in development it prints to the
console — no extra config needed either way.

---

## Deployment

Deployed as a single Docker image on Render. `docker-entrypoint.sh` runs
`migrate` → `collectstatic` → `gunicorn` on every container start, so there's no
separate manual migration step in normal operation (the entrypoint handles it) —
though when this repo's maintainer deploys, they do still run `migrate` by hand on
Render's Shell tab as a safety check before trusting an auto-deploy.

Two custom domains point at the same Render web service; `CanonicalDomainMiddleware`
301-redirects the secondary domain to whichever one is set as `PRIMARY_DOMAIN`, so
switching which domain is "canonical" is a one-line env var change, no DNS work.

A Render Cron Job runs `python manage.py fetch_news` hourly to refresh the landing
page's civil-rights news widget (pulls from ACLU, EFF, FIRE, Institute for Justice,
SCOTUSblog, and Reason RSS feeds).

---

## Testing accounts / promo codes

The app supports a lightweight "tester" cohort separate from full admin access —
useful for letting volunteers try the product without exposing the Django admin to
them:

- `User.is_tester` unlocks an example-stories dropdown on the story page and a small
  "Test mode" badge in the navbar. Granted/revoked in bulk from the admin's Users
  list.
- A single promo code with `auto_grants_tester=True` (seeded via
  `python manage.py seed_tester_promo`) lets a tester sign up, get marked as a
  tester, *and* get a free ($0) Stripe checkout — all from one code entered once at
  signup.
- `python manage.py revoke_testers` strips `is_tester` from every account at the end
  of a testing round; pair with `seed_tester_promo --deactivate` to retire the code
  so it can't be reused.

---

## What this app deliberately does *not* do

- It does not give legal advice, and says so repeatedly (signup, finalize page,
  footer, legal disclaimer page).
- It does not invent facts. The AI prompts are explicit: only extract what's
  actually in the user's story; leave anything unmentioned blank rather than guess.
- It does not auto-file anything with a court. The end product is a PDF the user
  reviews, downloads, and files (or takes to an attorney) themselves.

---

## Further reading

`REBUILD_HANDOFF.md` in this repo is a much more detailed, append-only engineering
log — useful if you're picking up active development on this project and want the
full history of *why* things are built the way they are, commit by commit.
