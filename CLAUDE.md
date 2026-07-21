# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this app is

AuditFile 1983 (live at auditfile1983.com) is a Django app that walks a user through
building a **Section 1983 federal civil rights complaint** (police misconduct,
wrongful arrest, excessive force, retaliation for filming, etc). It is explicitly
**not a law firm** and says so at signup, on the finalize page, and in the footer.

Flow: user writes their story (typed/dictated/added in chunks) → GPT-4o extracts
structured facts → a 7-step wizard lets the user review/correct everything → GPT
drafts first-person "factual allegations" → WeasyPrint renders a federal-court-
formatted PDF (watermarked until paid *and* finalized) → Stripe checkout → explicit
finalize step locks the document and unlocks a clean re-downloadable PDF.

**Read `README.md` first** — it's a full architecture writeup (tech stack, wizard
URL map, services table, data model, security). `REBUILD_HANDOFF.md` is an
append-only, commit-by-commit engineering log; skim its top "Where we are right
now" section for current status, open roadmap items, and the maintainer's stated
working preferences (step-by-step changes, wrap all commands/codes in code blocks,
Windows/PowerShell, prefers admin UI over terminal). Don't duplicate either file
here — this doc is the quick-orientation layer, not a replacement.

## Commands

```bash
# Local dev (Docker Compose: Postgres + web)
docker compose build web              # only when Dockerfile/requirements.txt change
docker compose up -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py loaddata example_stories
docker compose exec web python manage.py loaddata foundational_case_law
docker compose exec web python manage.py createsuperuser

# Tests (Django TestCase, GPT calls mocked — no real OpenAI/Stripe calls, no network)
docker compose exec web python manage.py test documents -v 2
docker compose exec web python manage.py test documents.tests.WizardEndToEndTest
docker compose exec web python manage.py test documents.tests.WizardEndToEndTest.test_full_happy_path_register_through_pdf
docker compose exec web python manage.py test documents.tests.StoryAddendumTest

# Direct DB access
docker compose exec db psql -U postgres -d file1983

# New migration after a models.py change
docker compose exec web python manage.py makemigrations <app>

# Manually exercise the GPT extraction prompt without touching the DB
docker compose exec web python manage.py test_gpt_extraction --example 3 --json-only

# Tester-cohort tooling (see README "Testing accounts / promo codes")
docker compose exec web python manage.py seed_tester_promo
docker compose exec web python manage.py revoke_testers
```

There's no separate lint/format tooling configured in this repo (no flake8/black/ruff
config, no JS build step — Bootstrap/Alpine are loaded as-is, no npm project).

Local dev needs a `.env` file (no `.env.example` is checked in) — see README.md
"Environment variables" for the full list. At minimum set `OPENAI_API_KEY` or the
wizard's Analyze step will fail.

## Architecture orientation

Three Django apps, deliberately separated by role:
- **`accounts`** — custom email-based `User` (no usernames), profile, legal
  acceptance, `SiteSettings`, `LegalDocument`.
- **`documents`** — the actual product. Every wizard model, the AI/PDF/Stripe/
  partner services, the wizard views, admin.
- **`public_pages`** — marketing site, legal pages, CMS stub (`CivilRightsPage` /
  `PageSection`), RSS news widget.

`documents/services/` holds all business logic that isn't a Django view — this is
where to look first for anything AI-, PDF-, payment-, or lookup-related
(`openai_service.py` for extraction, `complaint_drafter.py` for the narrative,
`caselaw_picker.py`, `court_lookup_service.py`, `county_lookup_service.py`,
`addendum_service.py`, `stripe_service.py`, `ai_quota.py`, `partner_stats.py` — see
README's table for what each does). Views should stay thin and delegate here.

**Two middleware live in `documents/middleware.py`** and matter for how requests
behave: `CanonicalDomainMiddleware` (301s non-canonical hosts to `PRIMARY_DOMAIN`)
and `CaptureReferralMiddleware` (reads `?ref=CODE`, validates against `PromoCode`,
stashes it in session for pre-filling `/pay/` and `/accounts/register/`).
`accounts/middleware.py:RequireLegalAcceptanceMiddleware` forces re-acceptance of
TOS/Privacy when `TOS_VERSION`/`PRIVACY_VERSION` bump past a user's stored version.

**Document locking is the central invariant.** A `Document` moves through
`payment_status`: draft → paid → finalized. `locked_at` (set only via the explicit
two-checkbox `/finalize/` flow) is what actually blocks edits — *not* payment status
alone. Every wizard view checks lock state via `_check_locked_redirect()` in
`documents/views.py` for both GET and POST. The PDF watermark is likewise gated on
`doc.is_locked()`, not on `payment_status == 'paid'` — a paid-but-unlocked preview is
still watermarked, specifically to prevent preview-then-keep-re-editing abuse.

**Two distinct paths write into the wizard models, and they must never cross:**
1. Full story (re-)analysis (`openai_service._populate_models`) — re-derives *every*
   field from the current story text and **clears fields no longer mentioned**. This
   is intentionally destructive; it always reflects the story as it stands *now*.
2. Addenda (`addendum_service.apply_addendum`, and the quick-add page's post-analysis
   submits) — merges new detail into one category **without deleting or overwriting**
   existing rows/manual edits; matches list rows by natural key (defendant by name,
   claim by amendment, evidence by URL or type+description).

Never make an addendum path destructive, and never make full re-analysis
non-destructive — each behavior is load-bearing for a specific UX guarantee
described in README.md ("The wizard flow, end to end").

**AI usage is bounded by two independent guardrails** (`documents/services/
ai_quota.py`, settings `AI_QUOTA_FREE`/`AI_QUOTA_PAID`/`AI_CALL_COOLDOWN_SECONDS`):
a hard per-document call cap, and a short cooldown so rapid clicking can't burn
through it. Any new AI-calling code path (extraction, drafting, addenda) needs to go
through this, the same way the existing ones do.

**Location/legal-authority data prefers static datasets over GPT guesses.**
`court_lookup_service.py` and `county_lookup_service.py` check bundled JSON datasets
(ZIP/city → court/county) before ever falling back to GPT, and leave a field blank
rather than show an unverifiable AI guess as if it were confident. Case law
(`caselaw_picker.py`) is drawn only from a small curated, fixture-seeded library
(`documents/fixtures/foundational_case_law.json`) — never live-fetched or
AI-generated. Follow this pattern for any new "looks-up-a-fact-about-the-world"
feature: static data first, AI only as an explicitly-labeled fallback.

**Every document view scopes by owner** — `Document.objects.get(slug=..., user=
request.user)` — there is no by-slug access without an ownership check. Preserve
that on any new document-scoped view.

Migrations are per-app and sequential (`documents/00NN_...`, `accounts/000N_...`);
grep `REBUILD_HANDOFF.md` for a migration number if you need to know what a specific
one did — it's documented commit-by-commit there.

Templates mirror the app layout (`templates/<app>/...`) plus a shared
`templates/base.html`. There is no frontend build step: Bootstrap 5.3 and Alpine.js
are the entire client-side stack, loaded via CDN/static files, with page-specific
interactivity written inline as Alpine components in the templates themselves.

## Conventions worth preserving

- Money is always integer cents (`*_CENTS` settings/fields), never floats.
- New settings that are meant to be tunable without a code change go through
  `python-decouple`'s `config(...)` in `config/settings.py`, with a real default.
- Management commands for one-off admin/ops tasks (tester cohort resets, promo
  seeding, RSS refresh) live under each app's `management/commands/`, not as ad hoc
  scripts — follow that pattern for similar operational tooling.
- Deploy is a single Docker image on Render; `docker-entrypoint.sh` runs migrate →
  collectstatic → gunicorn on every start, so there's no separate manual-migration
  step baked into normal deploys (though the maintainer still runs `migrate` by hand
  on Render's Shell as a safety check).
