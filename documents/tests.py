"""
End-to-end happy-path test for the §1983 wizard.

Walks one user from registration through every wizard step and finally to a
PDF download, using Django's test client. GPT calls are mocked at the service
boundary so the test runs offline and is deterministic.

Run:
    docker compose exec web python manage.py test documents
    # or just this case:
    docker compose exec web python manage.py test documents.tests.WizardEndToEndTest

What this test guards against:
    - URL/route regressions on any wizard step
    - View-layer field handling (POST keys, save behaviors, redirects)
    - WizardSession.current_step advancing correctly through the steps
    - Auto-selection of supporting case law from the foundational fixture
    - PDF rendering (the WeasyPrint pipeline runs end-to-end)

What this test does NOT guard against:
    - JavaScript-driven UI (Alpine.js) — covered by Playwright/Selenium later
    - The real GPT extraction quality — that's a separate manual sanity check
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from documents.models import (
    Document, IncidentOverview, Defendant, ConstitutionalClaim,
    Evidence, Witness, Damages, ReliefSought, GovernmentEntity,
    PriorComplaints, PdfBranding, CaseLaw,
)

User = get_user_model()


# Fake GPT extraction output — matches the shape openai_service.extract_story
# would normally return + write to the wizard models. Keeping it minimal but
# realistic so _populate_models has something to work with.
FAKE_AI_ANALYSIS = {
    'document': {'title': 'Test Complaint', 'jury_trial_demand': True},
    'plaintiff': {
        'full_name': 'Test User',
        'address': '123 Test Lane',
        'city': 'Denver',
        'state': 'CO',
        'zip_code': '80202',
        'phone': '(555) 123-4567',
        'email': 'test@example.com',
        'filing_pro_se': True,
    },
    'incident': {
        'incident_date': '2024-03-15',
        'incident_time': '14:30',
        'address': '500 Main Street',
        'city': 'Denver',
        'state': 'CO',
        'county': 'Denver',
        'location_description': 'Sidewalk in front of the police station',
        'location_type': 'public_sidewalk',
        'is_public_forum': True,
        'plaintiff_activity': 'Filming the exterior of the police station',
        'force_used': True,
        'equipment_seized_or_damaged': True,
    },
    'defendants': [
        {
            'full_name': 'Officer J. Smith',
            'badge_number': '4567',
            'rank_title': 'Officer',
            'agency_name': 'Denver Police Department',
            'capacity_sued': 'both',
            'acting_under_color_of_law': True,
            'is_supervisor': False,
        },
    ],
    'government_entity': {
        'entity_name': 'City and County of Denver',
        'entity_address': '1437 Bannock St, Denver, CO 80202',
        'policy_or_custom_description': '',
    },
    'constitutional_claims': [
        {'amendment': '1st_retaliation', 'how_violated': 'Arrested in retaliation for filming police.'},
        {'amendment': '4th_seizure', 'how_violated': 'Detained without probable cause.'},
    ],
    'evidence': [],
    'witnesses': [],
    'damages': {
        'physical_injury_description': 'Bruised wrists from tight handcuffs.',
        'emotional_distress_description': 'Anxiety after the encounter.',
        'lost_wages': '',
        'property_damage_amount': '',
        'punitive_basis': '',
    },
    'relief': {
        'compensatory_damages': True,
        'compensatory_amount': None,
        'punitive_damages': True,
        'declaratory_judgment': False,
        'injunctive_relief': False,
        'attorney_fees': True,
        'costs_of_suit': True,
        'other_relief': '',
    },
    'prior_complaints': {
        'filed_complaints': False,
        'description': '',
        'outcomes': '',
    },
}

FAKE_PARAGRAPHS = [
    'On March 15, 2024 at approximately 2:30 p.m., I was standing on the public sidewalk in front of the Denver Police Department.',
    'I was filming the exterior of the building with my phone.',
    'Officer J. Smith approached me and ordered me to stop filming.',
    'I told Officer Smith I was on a public sidewalk and continued recording.',
    'Officer Smith placed me in handcuffs and detained me.',
    'I was held for approximately twenty minutes before being released.',
]


def _mock_extract_story(session, dry_run=False):
    """
    Stand-in for documents.services.openai_service.extract_story.
    Pretends the real GPT call succeeded and writes the fake analysis into
    the wizard models the same way the real service does.
    """
    from documents.services.openai_service import _populate_models

    session.ai_analysis = FAKE_AI_ANALYSIS
    session.ai_extraction_succeeded = True
    session.status = 'analyzed'
    session.save()

    _populate_models(session, FAKE_AI_ANALYSIS)
    return FAKE_AI_ANALYSIS, None


def _mock_generate_factual_allegations(document):
    return list(FAKE_PARAGRAPHS), None


@override_settings(
    OPENAI_API_KEY='test-key-not-real',
    DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    # Disable WhiteNoise's hashed-manifest storage in tests — it requires
    # `collectstatic` to have populated staticfiles.json first, which the test
    # runner doesn't do. Plain StaticFilesStorage just resolves paths directly.
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
)
class WizardEndToEndTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Foundational case law fixture so the case-law strategy chooser has
        # something to map claims to.
        call_command('loaddata', 'foundational_case_law', verbosity=0)

    def test_full_happy_path_register_through_pdf(self):
        # ----- 1. Register -----
        register_response = self.client.post(reverse('accounts:register'), {
            'email': 'walker@example.com',
            'first_name': 'Walker',
            'last_name': 'Tester',
            'password1': 'CorrectHorseBatteryStaple1!',
            'password2': 'CorrectHorseBatteryStaple1!',
        })
        self.assertEqual(register_response.status_code, 302)
        self.assertEqual(register_response.url, reverse('documents:list'))

        user = User.objects.get(email='walker@example.com')
        self.assertEqual(user.first_name, 'Walker')

        # The register view auto-logs the user in.

        # ----- 2. Complete the profile -----
        self.client.post(reverse('accounts:profile'), {
            'first_name': 'Walker',
            'last_name': 'Tester',
            'email': 'walker@example.com',
            'phone': '(555) 010-1010',
            'address': '500 Main Street',
            'city': 'Denver',
            'state': 'CO',
            'zip_code': '80202',
        })
        user.refresh_from_db()
        self.assertTrue(user.has_complete_profile())

        # ----- 3. Create a document -----
        create_response = self.client.get(reverse('documents:create'))
        self.assertEqual(create_response.status_code, 302)
        doc = Document.objects.get(user=user)
        self.assertIsNotNone(doc.wizard_session)
        self.assertIsNotNone(doc.plaintiff_info)

        slug = doc.slug

        # ----- 4. Submit story + run (mocked) GPT extraction -----
        story_text = (
            'On March 15, 2024 around 2:30pm, I was filming the exterior of the '
            'Denver Police Department from the public sidewalk. Officer Smith '
            '(badge 4567) approached me, ordered me to stop, and arrested me '
            'when I refused. I was held for about 20 minutes and released.'
        )
        with patch(
            'documents.services.openai_service.extract_story',
            side_effect=_mock_extract_story,
        ):
            story_response = self.client.post(
                reverse('documents:wizard_story', kwargs={'document_slug': slug}),
                {'story_text': story_text, 'action': 'analyze'},
            )
        self.assertEqual(story_response.status_code, 302)
        self.assertIn('summary', story_response.url)

        # Extraction should have populated the wizard models
        self.assertEqual(doc.defendants.count(), 1)
        self.assertEqual(doc.constitutional_claims.count(), 2)

        # ----- 5. Step 1: Federal Jurisdiction -----
        # Pre-set the court so the form passes — the real Step 1 view auto-runs
        # the lookup service, which the test environment may not have data for.
        incident = doc.incident_overview
        incident.federal_district_court = 'United States District Court for the District of Colorado'
        incident.save()

        step1_response = self.client.post(
            reverse('documents:wizard_step1', kwargs={'document_slug': slug}),
            {
                'federal_district_court': incident.federal_district_court,
                'court_confirmed': 'on',
            },
        )
        self.assertEqual(step1_response.status_code, 302)
        incident.refresh_from_db()
        self.assertTrue(incident.court_confirmed)

        # ----- 6. Step 2: Incident Details -----
        step2_response = self.client.post(
            reverse('documents:wizard_step2', kwargs={'document_slug': slug}),
            {
                'incident_date': '2024-03-15',
                'incident_time': '14:30',
                'address': '500 Main Street',
                'city': 'Denver',
                'state': 'CO',
                'county': 'Denver',
                'location_description': 'Sidewalk in front of police station',
                'location_type': 'public_sidewalk',
                'is_public_forum': 'yes',
                'plaintiff_activity': 'Filming the police station',
                'force_used': 'yes',
                'equipment_seized_or_damaged': 'yes',
            },
        )
        self.assertEqual(step2_response.status_code, 302)

        # ----- 7. Step 3: Defendants + Government Entity -----
        existing_defendant = doc.defendants.first()
        step3_response = self.client.post(
            reverse('documents:wizard_step3', kwargs={'document_slug': slug}),
            {
                'defendant_count': 1,
                'def_0_pk': existing_defendant.pk,
                'def_0_full_name': 'Officer J. Smith',
                'def_0_badge_number': '4567',
                'def_0_rank_title': 'Officer',
                'def_0_agency_name': 'Denver Police Department',
                'def_0_capacity_sued': 'both',
                'def_0_acting_under_color_of_law': 'on',
                'entity_name': 'City and County of Denver',
                'entity_address': '1437 Bannock St, Denver, CO 80202',
                'policy_or_custom_description': '',
            },
        )
        self.assertEqual(step3_response.status_code, 302)
        self.assertEqual(doc.defendants.count(), 1)

        # ----- 8. Step 4: Constitutional Claims -----
        claims = list(doc.constitutional_claims.order_by('id'))
        step4_response = self.client.post(
            reverse('documents:wizard_step4', kwargs={'document_slug': slug}),
            {
                'claim_count': 2,
                'claim_0_pk': claims[0].pk,
                'claim_0_amendment': claims[0].amendment,
                'claim_0_how_violated': claims[0].how_violated,
                'claim_1_pk': claims[1].pk,
                'claim_1_amendment': claims[1].amendment,
                'claim_1_how_violated': claims[1].how_violated,
            },
        )
        self.assertEqual(step4_response.status_code, 302)

        # ----- 9. Step 5: Evidence + Witnesses (with timestamp) -----
        step5_response = self.client.post(
            reverse('documents:wizard_step5', kwargs={'document_slug': slug}),
            {
                'evidence_count': 1,
                'ev_0_pk': '',
                'ev_0_evidence_type': 'video',
                'ev_0_description': 'Cell phone video of the encounter.',
                'ev_0_date_and_time': 'March 15, 2024, 2:30 PM',
                'ev_0_recorded_by': 'Plaintiff',
                'ev_0_public_url': 'https://www.youtube.com/watch?v=abc123',
                'ev_0_key_timestamp': '1.30.45',  # period syntax should normalize to 01:30:45
                'ev_0_defendant_aware_of_recording': 'yes',
                'witness_count': 1,
                'wit_0_pk': '',
                'wit_0_full_name': 'Jane Witness',
                'wit_0_contact_info': '555-555-1234',
                'wit_0_relationship_to_plaintiff': 'Bystander',
                'wit_0_what_they_witnessed': 'Saw the entire arrest from across the street.',
                'wit_0_has_video': 'no',
                'wit_0_willing_to_testify': 'yes',
            },
        )
        self.assertEqual(step5_response.status_code, 302)
        self.assertEqual(doc.evidence.count(), 1)
        self.assertEqual(doc.witnesses.count(), 1)

        # Timestamp normalization: "1.30.45" should become "01:30:45"
        ev = doc.evidence.first()
        self.assertEqual(ev.key_timestamp, '01:30:45')

        # ----- 10. Step 6: Damages, Relief, Prior Complaints -----
        step6_response = self.client.post(
            reverse('documents:wizard_step6', kwargs={'document_slug': slug}),
            {
                'physical_injury_description': 'Bruised wrists from handcuffs.',
                'emotional_distress_description': 'Anxiety since the incident.',
                'lost_wages': '',
                'property_damage_amount': '',
                'punitive_basis': '',
                'compensatory_damages': 'on',
                'compensatory_amount': '5000.00',
                'punitive_damages': 'on',
                'declaratory_judgment': 'on',
                'injunctive_relief': 'on',
                'attorney_fees': 'on',
                'costs_of_suit': 'on',
                'other_relief': '',
                # filed_complaints not checked
            },
        )
        self.assertEqual(step6_response.status_code, 302)
        relief = doc.relief_sought
        self.assertTrue(relief.compensatory_damages)
        self.assertTrue(relief.attorney_fees)

        # ----- 11. Step 7: Final review (just GET — no POST) -----
        step7_response = self.client.get(
            reverse('documents:wizard_step7', kwargs={'document_slug': slug}),
        )
        self.assertEqual(step7_response.status_code, 200)
        self.assertContains(step7_response, 'Test User')  # plaintiff name from extraction
        self.assertContains(step7_response, 'Officer J. Smith')

        # ----- 12. Pick a case-law strategy (inline) -----
        caselaw_response = self.client.post(
            reverse('documents:wizard_caselaw_strategy', kwargs={'document_slug': slug}),
            {'caselaw_strategy': 'inline'},
        )
        self.assertEqual(caselaw_response.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(doc.caselaw_strategy, 'inline')

        # ----- 13. Step 7 should now show the auto-picked cases -----
        step7_with_cases = self.client.get(
            reverse('documents:wizard_step7', kwargs={'document_slug': slug}),
        )
        self.assertContains(step7_with_cases, 'Nieves v. Bartlett')  # 1st_retaliation
        self.assertContains(step7_with_cases, 'Terry v. Ohio')       # 4th_seizure
        self.assertContains(step7_with_cases, 'Monell')              # gov entity present

        # ----- 14. Generate draft (mocked GPT) -----
        with patch(
            'documents.services.complaint_drafter.generate_factual_allegations',
            side_effect=_mock_generate_factual_allegations,
        ):
            draft_response = self.client.get(
                reverse('documents:wizard_draft', kwargs={'document_slug': slug}),
            )
        self.assertEqual(draft_response.status_code, 200)
        doc.refresh_from_db()
        saved_paragraphs = doc.factual_allegations_json.get('paragraphs', [])
        self.assertEqual(saved_paragraphs, FAKE_PARAGRAPHS)
        self.assertContains(draft_response, 'Cell phone video of the encounter.')

        # ----- 15. Edit a paragraph and save -----
        edited_paragraphs = list(FAKE_PARAGRAPHS)
        edited_paragraphs[0] = 'On March 15, 2024 — corrected by the user.'
        post_data = {f'paragraph_{i}': p for i, p in enumerate(edited_paragraphs)}
        post_data['action'] = 'save'
        save_response = self.client.post(
            reverse('documents:wizard_draft', kwargs={'document_slug': slug}),
            post_data,
        )
        self.assertEqual(save_response.status_code, 302)
        doc.refresh_from_db()
        self.assertEqual(
            doc.factual_allegations_json['paragraphs'][0],
            'On March 15, 2024 — corrected by the user.',
        )

        # ----- 16. Generate the PDF -----
        pdf_response = self.client.get(
            reverse('documents:wizard_generate', kwargs={'document_slug': slug}),
        )
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
        self.assertGreater(len(pdf_response.content), 1000)
        self.assertTrue(pdf_response.content.startswith(b'%PDF'))

        # ----- 17. Final sanity: every step is now reachable -----
        for step in range(1, 8):
            url_name = f'documents:wizard_step{step}'
            r = self.client.get(reverse(url_name, kwargs={'document_slug': slug}))
            self.assertEqual(
                r.status_code, 200,
                msg=f'Step {step} should be reachable after completing the wizard',
            )


@override_settings(
    OPENAI_API_KEY='test-key-not-real',
    DEFAULT_AUTO_FIELD='django.db.models.BigAutoField',
    STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage',
)
class StoryAddendumTest(TestCase):
    """
    Verify that post-extraction addendums (the 'add details about X' modal on
    the summary page) merge new info into the wizard models WITHOUT deleting
    or overwriting confirmed data.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email='auditor@example.com',
            password='CorrectHorseBatteryStaple1!',
            first_name='Aud', last_name='Itor',
        )
        self.client.force_login(self.user)
        self.doc = Document.objects.create(user=self.user)
        from documents.models import WizardSession, PlaintiffInfo
        self.session = WizardSession.objects.create(
            document=self.doc,
            ai_extraction_succeeded=True,
            ai_analysis=FAKE_AI_ANALYSIS,
            status='analyzed',
            current_step=1,
        )
        PlaintiffInfo.objects.create(document=self.doc, full_name='Aud Itor')
        # Pre-populate models from the fake analysis the way the real extraction would
        from documents.services.openai_service import _populate_models
        _populate_models(self.session, FAKE_AI_ANALYSIS)

    def _post_addendum(self, category, text):
        return self.client.post(
            reverse('documents:wizard_addendum', kwargs={'document_slug': self.doc.slug}),
            {'category': category, 'text': text},
        )

    def test_addendum_adds_new_defendant_without_deleting_existing(self):
        """User dictates info about a second officer; the first one must remain."""
        self.assertEqual(self.doc.defendants.count(), 1)
        original = self.doc.defendants.first()
        original_name = original.full_name

        merged_response = {
            'defendants': [
                {
                    'full_name': 'Officer J. Smith', 'badge_number': '4567',
                    'rank_title': 'Officer', 'agency_name': 'Denver Police Department',
                    'capacity_sued': 'both', 'acting_under_color_of_law': True,
                    'is_supervisor': False,
                },
                {
                    'full_name': 'Sergeant Maria Lopez', 'badge_number': '8821',
                    'rank_title': 'Sergeant', 'agency_name': 'Denver Police Department',
                    'capacity_sued': 'both', 'acting_under_color_of_law': True,
                    'is_supervisor': True,
                },
            ],
            'government_entity': {
                'entity_name': 'City and County of Denver',
                'entity_address': '1437 Bannock St, Denver, CO 80202',
                'policy_or_custom_description': '',
            },
        }
        with patch(
            'documents.services.addendum_service._call_openai',
            return_value=('{"junk": true}', None),  # raw is ignored, _parse_json is patched too
        ), patch(
            'documents.services.addendum_service._parse_json',
            return_value=(merged_response, None),
        ):
            response = self._post_addendum(
                'defendants',
                'There was a second officer — Sergeant Maria Lopez, badge 8821, supervisor.',
            )
        self.assertEqual(response.status_code, 302)

        # Both defendants should now exist
        self.assertEqual(self.doc.defendants.count(), 2)
        names = sorted(d.full_name for d in self.doc.defendants.all())
        self.assertEqual(names, ['Officer J. Smith', 'Sergeant Maria Lopez'])

        # The original row should NOT have been deleted/recreated
        original.refresh_from_db()
        self.assertEqual(original.full_name, original_name)

        # Audit log should have an entry
        self.session.refresh_from_db()
        self.assertEqual(len(self.session.story_addendums), 1)
        self.assertEqual(self.session.story_addendums[0]['category'], 'defendants')

    def test_addendum_updates_existing_defendant_match_by_name(self):
        """If the addendum re-mentions an existing defendant, fields update in place."""
        original = self.doc.defendants.first()
        original_pk = original.pk

        merged_response = {
            'defendants': [{
                'full_name': 'Officer J. Smith', 'badge_number': '4567',
                'rank_title': 'Officer', 'agency_name': 'Denver Police Department',
                'parent_government_entity': 'City and County of Denver',
                'agency_address': '1331 Cherokee St, Denver, CO',
                'capacity_sued': 'both', 'acting_under_color_of_law': True,
                'color_of_law_basis': 'On duty in uniform.',
                'is_supervisor': False,
            }],
            'government_entity': {},
        }
        with patch(
            'documents.services.addendum_service._call_openai',
            return_value=('{}', None),
        ), patch(
            'documents.services.addendum_service._parse_json',
            return_value=(merged_response, None),
        ):
            self._post_addendum(
                'defendants',
                "Officer Smith was at 1331 Cherokee St, on duty in uniform.",
            )

        # Still one defendant — same row, updated fields
        self.assertEqual(self.doc.defendants.count(), 1)
        original.refresh_from_db()
        self.assertEqual(original.pk, original_pk)
        self.assertEqual(original.agency_address, '1331 Cherokee St, Denver, CO')
        self.assertEqual(original.color_of_law_basis, 'On duty in uniform.')

    def test_addendum_evidence_appends_new_record(self):
        """Adding evidence after the fact should create new rows (the original story had none)."""
        self.assertEqual(self.doc.evidence.count(), 0)
        merged_response = {
            'evidence': [{
                'evidence_type': 'video',
                'description': 'YouTube livestream of the incident',
                'public_url': 'https://youtu.be/abc123',
                'key_timestamp': '00:04:12',
                'recorded_by': 'Plaintiff',
            }],
        }
        with patch(
            'documents.services.addendum_service._call_openai',
            return_value=('{}', None),
        ), patch(
            'documents.services.addendum_service._parse_json',
            return_value=(merged_response, None),
        ):
            self._post_addendum(
                'evidence',
                'There is a YouTube video at https://youtu.be/abc123 — arrest happens at 4:12.',
            )
        self.assertEqual(self.doc.evidence.count(), 1)
        ev = self.doc.evidence.first()
        self.assertEqual(ev.public_url, 'https://youtu.be/abc123')
        self.assertEqual(ev.key_timestamp, '00:04:12')

    def test_addendum_rejects_unknown_category(self):
        response = self._post_addendum('not-a-real-category', 'anything')
        self.assertEqual(response.status_code, 302)
        # No addendum recorded
        self.session.refresh_from_db()
        self.assertEqual(self.session.story_addendums, [])

    def test_addendum_rejects_empty_text(self):
        response = self._post_addendum('defendants', '   ')
        self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.story_addendums, [])

    def test_summary_page_renders_addendum_buttons(self):
        response = self.client.get(
            reverse('documents:wizard_summary', kwargs={'document_slug': self.doc.slug})
        )
        self.assertEqual(response.status_code, 200)
        # The modal + at least one per-item Add button should be in the markup
        self.assertContains(response, 'addendum-modal')
        self.assertContains(response, "open('defendants'")
        self.assertContains(response, "Pick a category")
