"""
Add legal-acceptance audit fields to User and version + effective_date to
LegalDocument. Also seed the initial Terms of Service and Privacy Policy
records so the re-acceptance gate has something to show on first deploy.

The seeded copy is the heart of this whole feature: it makes clear that
the documents produced by File 1983 are AI-generated, that we are not a
law firm, that AI can and does make mistakes, that the user assumes all
responsibility for what they file, and that they should have a lawyer
review anything they're not sure about.
"""
from django.db import migrations, models


def seed_legal_documents(apps, schema_editor):
    LegalDocument = apps.get_model('accounts', 'LegalDocument')

    terms_html = '''
<h2 class="h4 mt-4">1. About this Service</h2>
<p>File 1983 (the "Service") is a self-help platform that helps you draft a
Section 1983 civil rights complaint. The Service uses artificial intelligence
to organize your story into a complaint document that you can review, edit,
and ultimately file in court yourself.</p>

<div class="alert alert-danger mt-4">
  <h5 class="alert-heading"><i class="bi bi-exclamation-octagon-fill me-2"></i>We are NOT a law firm and we are NOT your lawyer.</h5>
  <p class="mb-2">File 1983 does not provide legal advice. Reading the content
  on this site, using the wizard, generating a draft, or downloading a PDF
  does <strong>not</strong> create an attorney-client relationship.</p>
  <p class="mb-0">If you need legal advice about your case, your rights, the
  strength of your claims, the statute of limitations, or anything else, you
  should consult a licensed attorney in your jurisdiction.</p>
</div>

<h2 class="h4 mt-4">2. Artificial Intelligence — what it can and can't do</h2>
<p>The drafting features of this Service are powered by large language
models (AI). AI tools are useful but imperfect. By using the Service you
acknowledge and agree that:</p>
<ul>
  <li><strong>AI can and does make mistakes.</strong> It can misstate facts,
  miss facts, invent facts ("hallucinate"), miscite or misapply law,
  mis-format documents, and produce output that is incomplete, inaccurate,
  or unsuitable for filing.</li>
  <li>The Service may produce drafts that contain errors of fact, law, or
  procedure even when you have entered correct information.</li>
  <li>You are <strong>solely responsible</strong> for reviewing every word of
  any document you generate before relying on it, sharing it, or filing it
  with any court.</li>
  <li>If you are not certain that a generated document is accurate and
  appropriate for your situation, <strong>you must have it reviewed by a
  licensed attorney</strong> before you use it.</li>
</ul>

<h2 class="h4 mt-4">3. Your responsibilities</h2>
<p>You agree that:</p>
<ul>
  <li>You will provide accurate and truthful information about your case.</li>
  <li>You will read and review any draft, preview, or final document
  carefully before downloading, signing, or filing it.</li>
  <li>You understand that filing a complaint in federal court has serious
  legal consequences, including potential sanctions for frivolous filings,
  and that you take full responsibility for the contents of anything you
  submit to a court.</li>
  <li>You will not use the Service to file claims you know to be false,
  fraudulent, or harassing.</li>
</ul>

<h2 class="h4 mt-4">4. No legal-outcome guarantees</h2>
<p>We make no promise, warranty, or guarantee about the legal outcome of
any complaint drafted with the Service. Using this Service does not
guarantee that your complaint will be accepted by a court, that it will
survive a motion to dismiss, that you will prevail at trial, or that you
will recover any damages.</p>

<h2 class="h4 mt-4">5. Disclaimer of warranties</h2>
<p>The Service is provided <strong>"as is" and "as available"</strong>
without warranties of any kind, express or implied, including but not
limited to warranties of merchantability, fitness for a particular purpose,
accuracy, completeness, or non-infringement. We do not warrant that the
Service will be uninterrupted, error-free, secure, or that any AI output
will be accurate or reliable.</p>

<h2 class="h4 mt-4">6. Limitation of liability</h2>
<p>To the maximum extent permitted by law, File 1983, its operators,
employees, contractors, and affiliates are <strong>not liable</strong> for
any direct, indirect, incidental, consequential, special, exemplary, or
punitive damages, or for any loss of profits, revenues, data, goodwill, or
other intangible losses, arising out of or relating to your use of the
Service, including without limitation any errors, omissions, or
inaccuracies in any AI-generated document, any decision you make based on
the Service, or the outcome of any case you file. Your sole remedy if you
are dissatisfied with the Service is to stop using it.</p>

<h2 class="h4 mt-4">7. Indemnification</h2>
<p>You agree to indemnify and hold harmless File 1983 and its operators
from any claim, demand, loss, or expense (including reasonable attorney's
fees) arising out of (a) your use of the Service, (b) any document you
generate, sign, or file, (c) your violation of these Terms, or (d) your
violation of any law or third-party right.</p>

<h2 class="h4 mt-4">8. Accounts and acceptable use</h2>
<p>You are responsible for keeping your account credentials secure and for
all activity that occurs under your account. You agree not to attempt to
break, abuse, or reverse-engineer the Service, and not to use it to harass
or harm others.</p>

<h2 class="h4 mt-4">9. Payments</h2>
<p>Some features of the Service require payment. All payments are processed
through Stripe. Prices are shown at checkout. Once a document has been
finalized and downloaded as a clean (un-watermarked) PDF, the purchase is
final and non-refundable.</p>

<h2 class="h4 mt-4">10. Changes to these Terms</h2>
<p>We may update these Terms from time to time. When we make a material
change, we will increment the version of this document and require you to
re-accept the updated Terms before continuing to use the Service. Your
continued use after acceptance constitutes agreement to the new Terms.</p>

<h2 class="h4 mt-4">11. Governing law</h2>
<p>These Terms are governed by the laws of the United States and of the
state in which the Service is operated, without regard to conflict-of-laws
principles.</p>

<h2 class="h4 mt-4">12. Contact</h2>
<p>Questions about these Terms? Email us at
<a href="mailto:rights@auditfile1983.com">rights@auditfile1983.com</a>.</p>
'''.strip()

    privacy_html = '''
<h2 class="h4 mt-4">1. What we collect</h2>
<p>When you use File 1983 we collect the information you give us, including:</p>
<ul>
  <li>Account information (email, name, password hash)</li>
  <li>Profile and contact information you enter (address, phone)</li>
  <li>The story and case details you submit to the wizard</li>
  <li>Payment information processed by Stripe (we do not store full card
  numbers — Stripe handles that)</li>
  <li>Basic technical information (IP address, browser, pages visited) used
  for security and to operate the Service</li>
</ul>

<h2 class="h4 mt-4">2. How your story is used by AI</h2>
<p>The narrative you enter into the wizard is sent to a third-party AI
provider (OpenAI) to extract structured data and to generate draft
factual allegations. The information is sent over an encrypted connection
and is processed solely to produce your draft. By using the Service you
consent to this processing.</p>

<h2 class="h4 mt-4">3. How we use your information</h2>
<p>We use your information to:</p>
<ul>
  <li>Operate the Service (build your draft, generate PDFs, take payment)</li>
  <li>Send you transactional email (password resets, payment receipts,
  support replies)</li>
  <li>Detect and prevent abuse, fraud, and security issues</li>
  <li>Improve the Service over time</li>
</ul>

<h2 class="h4 mt-4">4. Who we share it with</h2>
<p>We share information only with the third parties we need to run the
Service:</p>
<ul>
  <li>Stripe — to process payments</li>
  <li>OpenAI — to generate AI-drafted content from your story</li>
  <li>Our hosting provider (Render) — to serve the Service</li>
  <li>Our email provider — to deliver transactional email</li>
</ul>
<p>We do not sell your personal information. We do not use it for
third-party advertising.</p>

<h2 class="h4 mt-4">5. Cookies and sessions</h2>
<p>We use cookies to keep you logged in, to remember your wizard progress,
and to track referral links. We do not use third-party advertising
trackers.</p>

<h2 class="h4 mt-4">6. Your data, your account</h2>
<p>You can edit your profile, view your documents, and reset your password
at any time. To delete your account or your stored case data, email us at
<a href="mailto:rights@auditfile1983.com">rights@auditfile1983.com</a> and
we will remove it within a reasonable time, subject to any legal record-
keeping obligations (for example, payment records).</p>

<h2 class="h4 mt-4">7. Security</h2>
<p>We use HTTPS, hashed passwords, and standard industry practices to
protect your information. No system is 100% secure, and we cannot guarantee
absolute security of any data transmitted to or stored by the Service.</p>

<h2 class="h4 mt-4">8. Children</h2>
<p>The Service is not intended for anyone under 18.</p>

<h2 class="h4 mt-4">9. Changes to this Policy</h2>
<p>We may update this Policy from time to time. When we make a material
change, we will increment the version and require you to re-accept the
updated Policy before continuing to use the Service.</p>

<h2 class="h4 mt-4">10. Contact</h2>
<p>Questions about this Policy? Email us at
<a href="mailto:rights@auditfile1983.com">rights@auditfile1983.com</a>.</p>
'''.strip()

    LegalDocument.objects.update_or_create(
        doc_type='terms',
        defaults={
            'title': 'Terms of Service',
            'content': terms_html,
            'version': 'v1',
        },
    )
    LegalDocument.objects.update_or_create(
        doc_type='privacy',
        defaults={
            'title': 'Privacy Policy',
            'content': privacy_html,
            'version': 'v1',
        },
    )


def unseed_legal_documents(apps, schema_editor):
    LegalDocument = apps.get_model('accounts', 'LegalDocument')
    LegalDocument.objects.filter(doc_type__in=['terms', 'privacy']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_is_revenue_partner'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='tos_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='tos_accepted_version',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='user',
            name='privacy_accepted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='privacy_accepted_version',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name='legaldocument',
            name='version',
            field=models.CharField(
                default='v1',
                help_text=(
                    'Version label shown to users and stamped onto each acceptance. '
                    'Bump this whenever the document changes substantively. For Terms '
                    'and Privacy, also update settings.TOS_VERSION / PRIVACY_VERSION '
                    'so existing users are forced to re-accept on next visit.'
                ),
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='legaldocument',
            name='effective_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='legaldocument',
            name='doc_type',
            field=models.CharField(
                choices=[
                    ('terms', 'Terms of Service'),
                    ('privacy', 'Privacy Policy'),
                    ('disclaimer', 'Legal Disclaimer'),
                    ('cookies', 'Cookie Policy'),
                ],
                max_length=20,
                unique=True,
            ),
        ),
        migrations.RunPython(seed_legal_documents, unseed_legal_documents),
    ]
