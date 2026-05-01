"""
documents/services/caselaw_picker.py

Maps each ConstitutionalClaim.amendment to a foundational CaseLaw row from the
curated library. Used by the draft + PDF templates to render supporting
authority based on Document.caselaw_strategy.

This is "Option A" — auto-pick the controlling case for each amendment. The
fixture is ordered (order=1 is the leading case in each category), so we just
take the top hit per category.

A future "Option B" would let users curate per-claim picks; this helper would
then become the fallback when the user hasn't picked anything.
"""

from documents.models import CaseLaw


# Map ConstitutionalClaim.AMENDMENT_CHOICES keys to CaseLaw.CATEGORY_CHOICES.
# The fixture has cases for the categories on the right side; missing entries
# are intentional — we don't have curated cases for those amendments yet, so
# those claims won't get supporting authority attached. (Better to omit than
# to cite an unrelated case.)
AMENDMENT_CATEGORY_MAP = {
    '1st':                 '1st_recording',     # filming police is the canonical 1st Am claim here
    '1st_retaliation':     '1st_retaliation',
    '1st_prior_restraint': '1st_recording',
    '1st_viewpoint':       '1st_recording',
    '4th_search':          '4th_seizure',       # closest available; fixture has no 4th_search yet
    '4th_seizure':         '4th_seizure',
    '4th_property':        '4th_seizure',
    '4th_excessive_force': '4th_excessive_force',
    # 5th, 6th, 8th, 14th — no curated cases yet, intentionally absent
    'other':               None,
}


def select_supporting_cases(document):
    """
    Return a list of dicts describing which CaseLaw rows support which claims:

        [
            {'claim': <ConstitutionalClaim>, 'case': <CaseLaw>, 'kind': 'claim'},
            ...
            {'claim': None, 'case': <Monell>, 'kind': 'monell'},   # if applicable
        ]

    Empty list means no supporting authority will be rendered (either because
    no claims map to a curated category, or strategy='none' should suppress it
    upstream — this helper does not check the strategy).

    Deduplicates by case so the appendix doesn't list the same case twice if
    two claims share a category.
    """
    results = []
    seen_case_ids = set()

    claims = list(document.constitutional_claims.all())

    for claim in claims:
        category = AMENDMENT_CATEGORY_MAP.get(claim.amendment)
        if not category:
            continue

        case = (
            CaseLaw.objects
            .filter(category=category, is_active=True)
            .order_by('order', '-year')
            .first()
        )
        if not case:
            continue

        results.append({'claim': claim, 'case': case, 'kind': 'claim'})

    # Add Monell if there's a named municipal defendant. Only include once
    # even if the user has multiple claims.
    gov_entity = getattr(document, 'government_entity', None)
    if gov_entity and (gov_entity.entity_name or '').strip():
        monell = (
            CaseLaw.objects
            .filter(category='monell', is_active=True)
            .order_by('order', '-year')
            .first()
        )
        if monell and monell.id not in {r['case'].id for r in results}:
            results.append({'claim': None, 'case': monell, 'kind': 'monell'})

    # Deduplicate by case_id (preserve order of first occurrence)
    deduped = []
    for r in results:
        if r['case'].id in seen_case_ids:
            continue
        seen_case_ids.add(r['case'].id)
        deduped.append(r)

    return deduped
