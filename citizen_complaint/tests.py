"""
End-to-end tests for the Citizen Complaint Assistant, mirroring the style of
documents/tests.py:WizardEndToEndTest. External calls (YouTube/Supadata/
OpenAI/Google Search) are mocked at the service boundary so the suite runs
offline and deterministically.

Run:
    python manage.py test citizen_complaint
"""
from unittest.mock import patch

from django.conf import settings as dj_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Incident, TargetAgency, Complaint
from .services import api_quota, rate_limit, moderation

User = get_user_model()


def _make_verified_user(**kwargs):
    """Creates a user who has already accepted TOS/Privacy (so
    RequireLegalAcceptanceMiddleware doesn't bounce every request to
    /accounts/accept-terms/) and verified their email."""
    user = User.objects.create_user(**kwargs)
    user.tos_accepted_version = dj_settings.TOS_VERSION
    user.privacy_accepted_version = dj_settings.PRIVACY_VERSION
    user.email_verified = True
    user.save()
    return user


# Matches documents/tests.py's WizardEndToEndTest override — WhiteNoise's
# hashed-manifest storage requires collectstatic to have run first, which the
# test runner doesn't do.
_TEST_OVERRIDES = dict(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')


def _fake_run_intake(incident):
    """Bypasses all external calls but exercises the same DB writes run_intake does."""
    incident.video_platform = 'youtube'
    incident.video_title = 'Officer stops me for filming at the library'
    incident.video_description = 'Filmed at the Saint Louis Public Library today.'
    incident.transcript = 'I was standing outside the Saint Louis Public Library recording.'
    incident.extracted_data = {
        'agencies': ['Saint Louis Public Library', 'Saint Louis Metropolitan Police Department'],
        'location': 'Saint Louis, MO',
        'incident_date': '2026-01-01',
        'contacts': [],
        'summary': 'The user was filming outside a public library when police were called.',
        'regex': {'emails': [], 'phones': [], 'addresses': [], 'links': []},
    }
    incident.status = 'agencies_reviewed'
    incident.current_step = 1
    incident.save()
    TargetAgency.objects.create(
        incident=incident, name='Saint Louis Public Library', email='library@example.gov',
        source='db_match', order=0,
    )
    TargetAgency.objects.create(
        incident=incident, name='Saint Louis Metropolitan Police Department', email='',
        source='detected', order=1,
    )
    return True, 'Video processed.'


@override_settings(**_TEST_OVERRIDES)
class CitizenComplaintEndToEndTest(TestCase):
    def setUp(self):
        self.user = _make_verified_user(
            email='citizen@example.com', password='testpass123',
            first_name='Alex', last_name='Doe',
        )
        self.client.force_login(self.user)

        # Moderation defaults to "clean" for every test in this class (real
        # OpenAI calls would fail closed with no key configured). The one
        # test that wants flagged behavior overrides self.mock_moderation
        # .return_value directly.
        moderation_patcher = patch(
            'citizen_complaint.services.moderation.check_content', return_value=(False, [], ''),
        )
        self.mock_moderation = moderation_patcher.start()
        self.addCleanup(moderation_patcher.stop)

    def test_landing_page_public(self):
        self.client.logout()
        resp = self.client.get(reverse('citizen_complaint:landing'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Citizen Complaint Assistant')

    def test_my_complaints_list_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('citizen_complaint:list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    def test_my_complaints_list_shows_own_incidents_only(self):
        mine = Incident.objects.create(user=self.user, video_url='https://youtu.be/mine', video_title='My video')
        other_user = _make_verified_user(email='other@example.com', password='testpass123')
        Incident.objects.create(user=other_user, video_url='https://youtu.be/other', video_title='Other video')

        resp = self.client.get(reverse('citizen_complaint:list'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'My video')
        self.assertNotContains(resp, 'Other video')

    def test_my_complaints_continue_link_routes_by_current_step(self):
        incident = Incident.objects.create(user=self.user, video_url='https://youtu.be/x', current_step=2)
        self.assertEqual(incident.next_step_url_name(), 'citizen_complaint:about_you')
        incident.status = 'sent'
        self.assertEqual(incident.next_step_url_name(), 'citizen_complaint:sent')

    def test_new_incident_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse('citizen_complaint:new'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp.url)

    @patch('citizen_complaint.services.video_intake.run_intake', side_effect=_fake_run_intake)
    def test_full_happy_path_sends_email(self, mock_intake):
        # Step 0 — intake
        resp = self.client.post(reverse('citizen_complaint:new'), {
            'video_url': 'https://www.youtube.com/watch?v=abc123',
        })
        incident = Incident.objects.get(user=self.user)
        self.assertRedirects(resp, reverse('citizen_complaint:agencies', args=[incident.slug]))

        library = incident.target_agencies.get(name='Saint Louis Public Library')
        pd = incident.target_agencies.get(name='Saint Louis Metropolitan Police Department')

        # Step 1 — confirm agencies, fill in the missing PD email
        resp = self.client.post(reverse('citizen_complaint:agencies', args=[incident.slug]), {
            f'confirmed_{library.id}': 'on',
            f'email_{library.id}': library.email,
            f'role_{library.id}': 'Venue — policy violation',
            f'confirmed_{pd.id}': 'on',
            f'email_{pd.id}': 'pd@example.gov',
            f'role_{pd.id}': 'Responding officers — unlawful detention',
            'action': 'continue',
        })
        self.assertRedirects(resp, reverse('citizen_complaint:about_you', args=[incident.slug]))
        pd.refresh_from_db()
        self.assertEqual(pd.email, 'pd@example.gov')
        self.assertTrue(pd.confirmed)

        # Step 2 — about you
        resp = self.client.post(reverse('citizen_complaint:about_you', args=[incident.slug]), {
            'privacy_level': 'full_name',
            'user_city': 'Saint Louis',
            'user_state': 'MO',
            'contact_email': 'reply-here@example.com',
            'personal_note': 'This has happened to me before at this branch.',
            'tone': 'factual',
        })
        self.assertRedirects(resp, reverse('citizen_complaint:drafts', args=[incident.slug]))

        # Step 3 — drafts (GPT call mocked so no OPENAI_API_KEY needed)
        with patch('citizen_complaint.services.complaint_drafter.generate_draft',
                   return_value=('Dear Sir/Madam, ... — Alex Doe', None)):
            resp = self.client.get(reverse('citizen_complaint:drafts', args=[incident.slug]))
            self.assertEqual(resp.status_code, 200)

        complaints = Complaint.objects.filter(incident=incident)
        self.assertEqual(complaints.count(), 2)
        for c in complaints:
            self.assertTrue(c.body)
            self.assertIsNotNone(c.viewed_at)

        resp = self.client.post(reverse('citizen_complaint:drafts', args=[incident.slug]), {
            'action': 'continue',
        })
        self.assertRedirects(resp, reverse('citizen_complaint:send', args=[incident.slug]))

        # Step 4 — send
        resp = self.client.get(reverse('citizen_complaint:send', args=[incident.slug]))
        self.assertEqual(resp.status_code, 200)

        post_data = {f'send_{c.id}': 'on' for c in complaints}
        resp = self.client.post(reverse('citizen_complaint:send', args=[incident.slug]), post_data)
        self.assertRedirects(resp, reverse('citizen_complaint:sent', args=[incident.slug]))

        self.assertEqual(len(mail.outbox), 2)
        sent_to = {m.to[0] for m in mail.outbox}
        self.assertEqual(sent_to, {'library@example.gov', 'pd@example.gov'})
        for m in mail.outbox:
            self.assertEqual(m.bcc, ['citizen@example.com'])
            self.assertEqual(m.reply_to, ['reply-here@example.com'])
            self.assertIn('Alex Doe via AuditFile 1983', m.from_email)

        for c in complaints:
            c.refresh_from_db()
            self.assertEqual(c.status, 'sent')
            self.assertIsNotNone(c.sent_at)

    @patch('citizen_complaint.services.video_intake.run_intake', side_effect=_fake_run_intake)
    @patch('citizen_complaint.services.complaint_drafter.generate_draft',
           return_value=('Dear Sir/Madam, ...', None))
    def test_anonymous_privacy_omits_reply_to_and_name(self, mock_draft, mock_intake):
        self.client.post(reverse('citizen_complaint:new'), {'video_url': 'https://youtu.be/xyz'})
        incident = Incident.objects.get(user=self.user)
        ta = incident.target_agencies.first()

        self.client.post(reverse('citizen_complaint:agencies', args=[incident.slug]), {
            f'confirmed_{ta.id}': 'on', f'email_{ta.id}': ta.email or 'agency@example.gov',
            'action': 'continue',
        })
        self.client.post(reverse('citizen_complaint:about_you', args=[incident.slug]), {
            'privacy_level': 'anonymous', 'contact_email': 'should-be-ignored@example.com', 'tone': 'factual',
        })
        self.client.get(reverse('citizen_complaint:drafts', args=[incident.slug]))
        self.client.post(reverse('citizen_complaint:drafts', args=[incident.slug]), {'action': 'continue'})

        complaint = Complaint.objects.get(incident=incident)
        self.client.post(reverse('citizen_complaint:send', args=[incident.slug]), {f'send_{complaint.id}': 'on'})

        incident.refresh_from_db()
        self.assertEqual(incident.display_name(), 'A concerned citizen')
        sent = mail.outbox[-1]
        self.assertEqual(sent.bcc, ['citizen@example.com'])
        self.assertEqual(sent.reply_to, [])
        self.assertIn('A concerned citizen via AuditFile 1983', sent.from_email)

    def test_send_blocked_without_email_verification(self):
        self.user.email_verified = False
        self.user.save()
        incident = Incident.objects.create(user=self.user, video_url='https://youtu.be/abc')
        ta = TargetAgency.objects.create(incident=incident, name='Agency', email='a@example.gov', confirmed=True, source='manual')
        Complaint.objects.create(incident=incident, target_agency=ta, body='draft body')

        complaint = Complaint.objects.get(incident=incident)
        resp = self.client.post(reverse('citizen_complaint:send', args=[incident.slug]), {f'send_{complaint.id}': 'on'})
        self.assertRedirects(resp, reverse('citizen_complaint:send', args=[incident.slug]))
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(CITIZEN_COMPLAINT_INCIDENTS_PER_USER_PER_DAY=1)
    @patch('citizen_complaint.services.video_intake.run_intake', side_effect=_fake_run_intake)
    def test_daily_new_incident_cap(self, mock_intake):
        self.client.post(reverse('citizen_complaint:new'), {'video_url': 'https://youtu.be/one'})
        self.assertEqual(Incident.objects.filter(user=self.user).count(), 1)

        resp = self.client.post(reverse('citizen_complaint:new'), {'video_url': 'https://youtu.be/two'})
        self.assertEqual(resp.status_code, 200)  # re-rendered form, not redirected
        self.assertEqual(Incident.objects.filter(user=self.user).count(), 1)

    def test_moderation_blocks_flagged_content(self):
        incident = Incident.objects.create(user=self.user, video_url='https://youtu.be/abc')
        ta = TargetAgency.objects.create(incident=incident, name='Agency', email='a@example.gov', confirmed=True, source='manual')
        complaint = Complaint.objects.create(incident=incident, target_agency=ta, body='draft body')

        self.mock_moderation.return_value = (True, ['violence/threats'], '')
        resp = self.client.post(reverse('citizen_complaint:send', args=[incident.slug]), {f'send_{complaint.id}': 'on'})

        self.assertRedirects(resp, reverse('citizen_complaint:send', args=[incident.slug]))
        self.assertEqual(len(mail.outbox), 0)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'draft')
        self.assertTrue(complaint.moderation_flagged)
        self.assertEqual(complaint.moderation_categories, ['violence/threats'])
        self.assertIsNotNone(complaint.moderation_checked_at)

    def test_moderation_check_failure_blocks_send(self):
        """Fails closed: if the moderation call itself errors, don't send."""
        incident = Incident.objects.create(user=self.user, video_url='https://youtu.be/abc')
        ta = TargetAgency.objects.create(incident=incident, name='Agency', email='a@example.gov', confirmed=True, source='manual')
        complaint = Complaint.objects.create(incident=incident, target_agency=ta, body='draft body')

        self.mock_moderation.return_value = (True, [], 'OpenAI API unreachable')
        self.client.post(reverse('citizen_complaint:send', args=[incident.slug]), {f'send_{complaint.id}': 'on'})

        self.assertEqual(len(mail.outbox), 0)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'draft')

    @override_settings(CITIZEN_COMPLAINT_AGENCY_SENDS_PER_DAY=0)
    def test_agency_daily_cap_blocks_send(self):
        incident = Incident.objects.create(user=self.user, video_url='https://youtu.be/abc')
        ta = TargetAgency.objects.create(incident=incident, name='Agency', email='capped@example.gov', confirmed=True, source='manual')
        complaint = Complaint.objects.create(incident=incident, target_agency=ta, body='draft body')

        self.client.post(reverse('citizen_complaint:send', args=[incident.slug]), {f'send_{complaint.id}': 'on'})
        self.assertEqual(len(mail.outbox), 0)
        complaint.refresh_from_db()
        self.assertEqual(complaint.status, 'draft')


class ApiQuotaTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='quota@example.com', password='testpass123')
        self.incident = Incident.objects.create(user=self.user, video_url='https://youtu.be/abc')

    @override_settings(CITIZEN_COMPLAINT_AI_QUOTA_PER_INCIDENT=2, CITIZEN_COMPLAINT_AI_CALL_COOLDOWN_SECONDS=0)
    def test_quota_exhausts(self):
        api_quota.consume_call(self.incident)
        api_quota.consume_call(self.incident)
        with self.assertRaises(api_quota.QuotaExceeded):
            api_quota.consume_call(self.incident)

    def test_cooldown_blocks_rapid_calls(self):
        api_quota.consume_call_throttled(self.incident)
        with self.assertRaises(api_quota.AICallTooSoon):
            api_quota.consume_call_throttled(self.incident)

    def test_plain_consume_call_ignores_cooldown(self):
        """Chained calls within one already-user-triggered pipeline (e.g. video
        intake's metadata + transcript + extraction) must not throttle each other."""
        api_quota.consume_call_throttled(self.incident)
        api_quota.consume_call(self.incident)  # should not raise despite active cooldown
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.api_calls_used, 2)


class ModerationTest(TestCase):
    def test_blank_text_is_never_flagged(self):
        flagged, categories, error = moderation.check_content('')
        self.assertFalse(flagged)
        self.assertEqual(categories, [])

    @override_settings(OPENAI_API_KEY='')
    def test_missing_api_key_fails_closed(self):
        flagged, categories, error = moderation.check_content('some complaint text')
        self.assertTrue(flagged)
        self.assertTrue(error)

    @override_settings(OPENAI_API_KEY='test-key-not-real')
    def test_openai_call_failure_fails_closed(self):
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.side_effect = Exception('network error')
            flagged, categories, error = moderation.check_content('some complaint text')
        self.assertTrue(flagged)
        self.assertTrue(error)

    @override_settings(OPENAI_API_KEY='test-key-not-real')
    def test_clean_content_passes(self):
        mock_result = type('Result', (), {
            'flagged': False,
            'categories': type('Categories', (), {'model_dump': lambda self: {'violence': False, 'harassment': False}})(),
        })()
        mock_response = type('Response', (), {'results': [mock_result]})()
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value.moderations.create.return_value = mock_response
            flagged, categories, error = moderation.check_content('Please review this incident.')
        self.assertFalse(flagged)
        self.assertEqual(categories, [])
        self.assertEqual(error, '')

    @override_settings(OPENAI_API_KEY='test-key-not-real')
    def test_describing_violence_experienced_is_not_blocked(self):
        """A citizen describing excessive force done TO them must not be
        blocked just because OpenAI's raw `flagged` trips on 'violence' —
        that would break the feature for nearly every real complaint."""
        mock_result = type('Result', (), {
            'flagged': True,  # OpenAI's own aggregate flag trips here
            'categories': type('Categories', (), {'model_dump': lambda self: {
                'violence': True, 'violence_graphic': True, 'harassment_threatening': False,
            }})(),
        })()
        mock_response = type('Response', (), {'results': [mock_result]})()
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value.moderations.create.return_value = mock_response
            flagged, categories, error = moderation.check_content(
                'The officer struck me with his baton and I was tackled to the ground.'
            )
        self.assertFalse(flagged)
        self.assertIn('violence', categories)  # still recorded for admin/audit
        self.assertEqual(error, '')

    @override_settings(OPENAI_API_KEY='test-key-not-real')
    def test_actual_threat_is_blocked(self):
        mock_result = type('Result', (), {
            'flagged': True,
            'categories': type('Categories', (), {'model_dump': lambda self: {
                'violence': False, 'harassment_threatening': True,
            }})(),
        })()
        mock_response = type('Response', (), {'results': [mock_result]})()
        with patch('openai.OpenAI') as mock_openai:
            mock_openai.return_value.moderations.create.return_value = mock_response
            flagged, categories, error = moderation.check_content('I will find you and hurt you.')
        self.assertTrue(flagged)
        self.assertIn('harassment_threatening', categories)


class RateLimitTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='rate@example.com', password='testpass123')

    def test_incidents_per_day(self):
        for _ in range(5):
            Incident.objects.create(user=self.user, video_url='https://youtu.be/x')
        self.assertFalse(rate_limit.can_start_incident(self.user))

    def test_agency_send_cap(self):
        incident = Incident.objects.create(user=self.user, video_url='https://youtu.be/x')
        for i in range(20):
            ta = TargetAgency.objects.create(incident=incident, name=f'A{i}', email='same@example.gov', confirmed=True)
            Complaint.objects.create(
                incident=incident, target_agency=ta, body='x', status='sent',
                sent_at=timezone.now(), recipient_email_snapshot='same@example.gov',
            )
        self.assertFalse(rate_limit.can_send_to_agency('same@example.gov'))
