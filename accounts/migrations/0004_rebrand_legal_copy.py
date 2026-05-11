"""
Rebrand seeded legal copy from "File 1983" to "AuditFile 1983" and add
explicit owner / representative language to the limitation-of-liability
and indemnification clauses.

Idempotent: uses update_or_create so it works whether or not the
preceding 0003 seed has already been applied to a deployed database.
Also nudges the SiteSettings singleton to the canonical brand name if
it's still on the original "File 1983" default.
"""
from django.db import migrations, models


TERMS_HTML = '''
<h2 class="h4 mt-4">1. About this Service</h2>
<p>AuditFile 1983 (the "Service") is a self-help platform that helps you
draft a Section 1983 civil rights complaint. The Service uses artificial
intelligence to organize your story into a complaint document that you can
review, edit, and ultimately file in court yourself.</p>

<div class="alert alert-danger mt-4">
  <h5 class="alert-heading"><i class="bi bi-exclamation-octagon-fill me-2"></i>We are NOT a law firm and we are NOT your lawyer.</h5>
  <p class="mb-2">AuditFile 1983 does not provide legal advice. Reading the
  content on this site, using the wizard, generating a draft, or downloading
  a PDF does <strong>not</strong> create an attorney-client relationship
  between you and AuditFile 1983, its owners, operators, or anyone else
  associated with the Service.</p>
  <p class="mb-0">If you need legal advice about your case, your rights, the
  strength of your claims, the statute of limitations, or anything else, you
  should consult a licensed attorney in your jurisdiction.</p>
</div>

<h2 class="h4 mt-4">2. Who we are</h2>
<p>The Service is owned and operated by the proprietors of
auditfile1983.com (the "Operators"). References in these Terms to
"AuditFile 1983," "we," "us," or "our" mean AuditFile 1983 together with
its owners, officers, members, employees, contractors, agents,
representatives, affiliates, and successors (collectively, the "AuditFile
1983 Parties").</p>

<h2 class="h4 mt-4">3. Artificial Intelligence — what it can and can't do</h2>
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

<h2 class="h4 mt-4">4. Your responsibilities</h2>
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

<h2 class="h4 mt-4">5. No legal-outcome guarantees</h2>
<p>We make no promise, warranty, or guarantee about the legal outcome of
any complaint drafted with the Service. Using this Service does not
guarantee that your complaint will be accepted by a court, that it will
survive a motion to dismiss, that you will prevail at trial, or that you
will recover any damages.</p>

<h2 class="h4 mt-4">6. Disclaimer of warranties</h2>
<p>The Service is provided <strong>"as is" and "as available"</strong>
without warranties of any kind, express or implied, including but not
limited to warranties of merchantability, fitness for a particular purpose,
accuracy, completeness, or non-infringement. We do not warrant that the
Service will be uninterrupted, error-free, secure, or that any AI output
will be accurate or reliable.</p>

<h2 class="h4 mt-4">7. Limitation of liability</h2>
<p>To the maximum extent permitted by law, the AuditFile 1983 Parties —
including without limitation AuditFile 1983 itself and its owners,
officers, members, employees, contractors, agents, representatives,
affiliates, and successors — are <strong>not liable</strong> for any
direct, indirect, incidental, consequential, special, exemplary, or
punitive damages, or for any loss of profits, revenues, data, goodwill, or
other intangible losses, arising out of or relating to your use of the
Service. This includes without limitation any errors, omissions, or
inaccuracies in any AI-generated document, any decision you make based on
the Service, any claim that the Service constitutes the unauthorized
practice of law, and the outcome of any case you file. Your sole remedy if
you are dissatisfied with the Service is to stop using it.</p>

<h2 class="h4 mt-4">8. Indemnification</h2>
<p>You agree to indemnify, defend, and hold harmless the AuditFile 1983
Parties — including AuditFile 1983 and its owners, officers, members,
employees, contractors, agents, representatives, and affiliates — from
and against any claim, demand, loss, liability, judgment, settlement, or
expense (including reasonable attorney's fees and costs) arising out of
or relating to (a) your use of the Service, (b) any document you generate,
sign, or file, (c) your violation of these Terms, (d) your violation of
any law or third-party right, or (e) any allegation that any document
produced through the Service caused you or any third party harm.</p>

<h2 class="h4 mt-4">9. Accounts and acceptable use</h2>
<p>You are responsible for keeping your account credentials secure and for
all activity that occurs under your account. You agree not to attempt to
break, abuse, or reverse-engineer the Service, and not to use it to harass
or harm others.</p>

<h2 class="h4 mt-4">10. Payments</h2>
<p>Some features of the Service require payment. All payments are processed
through Stripe. Prices are shown at checkout. Once a document has been
finalized and downloaded as a clean (un-watermarked) PDF, the purchase is
final and non-refundable.</p>

<h2 class="h4 mt-4">11. Changes to these Terms</h2>
<p>We may update these Terms from time to time. When we make a material
change, we will increment the version of this document and require you to
re-accept the updated Terms before continuing to use the Service. Your
continued use after acceptance constitutes agreement to the new Terms.</p>

<h2 class="h4 mt-4">12. Governing law</h2>
<p>These Terms are governed by the laws of the United States and of the
state in which the Service is operated, without regard to conflict-of-laws
principles.</p>

<h2 class="h4 mt-4">13. Contact</h2>
<p>Questions about these Terms? Email us at
<a href="mailto:rights@auditfile1983.com">rights@auditfile1983.com</a>.</p>
'''.strip()


PRIVACY_HTML = '''
<h2 class="h4 mt-4">1. About this Policy</h2>
<p>This Privacy Policy describes how AuditFile 1983 (the "Service"), owned
and operated by the proprietors of auditfile1983.com (the "Operators"),
collects, uses, and protects information about you when you use the
Service. References to "we," "us," or "our" mean AuditFile 1983 together
with its owners, employees, contractors, agents, and representatives.</p>

<h2 class="h4 mt-4">2. What we collect</h2>
<p>When you use AuditFile 1983 we collect the information you give us, including:</p>
<ul>
  <li>Account information (email, name, password hash)</li>
  <li>Profile and contact information you enter (address, phone)</li>
  <li>The story and case details you submit to the wizard</li>
  <li>Payment information processed by Stripe (we do not store full card
  numbers — Stripe handles that)</li>
  <li>Basic technical information (IP address, browser, pages visited) used
  for security and to operate the Service</li>
</ul>

<h2 class="h4 mt-4">3. How your story is used by AI</h2>
<p>The narrative you enter into the wizard is sent to a third-party AI
provider (OpenAI) to extract structured data and to generate draft
factual allegations. The information is sent over an encrypted connection
and is processed solely to produce your draft. By using the Service you
consent to this processing.</p>

<h2 class="h4 mt-4">4. How we use your information</h2>
<p>We use your information to:</p>
<ul>
  <li>Operate the Service (build your draft, generate PDFs, take payment)</li>
  <li>Send you transactional email (password resets, payment receipts,
  support replies)</li>
  <li>Detect and prevent abuse, fraud, and security issues</li>
  <li>Improve the Service over time</li>
</ul>

<h2 class="h4 mt-4">5. Who we share it with</h2>
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

<h2 class="h4 mt-4">6. Cookies and sessions</h2>
<p>We use cookies to keep you logged in, to remember your wizard progress,
and to track referral links. We do not use third-party advertising
trackers.</p>

<h2 class="h4 mt-4">7. Your data, your account</h2>
<p>You can edit your profile, view your documents, and reset your password
at any time. To delete your account or your stored case data, email us at
<a href="mailto:rights@auditfile1983.com">rights@auditfile1983.com</a> and
we will remove it within a reasonable time, subject to any legal record-
keeping obligations (for example, payment records).</p>

<h2 class="h4 mt-4">8. Security</h2>
<p>We use HTTPS, hashed passwords, and standard industry practices to
protect your information. No system is 100% secure, and the AuditFile 1983
Parties cannot guarantee absolute security of any data transmitted to or
stored by the Service.</p>

<h2 class="h4 mt-4">9. Children</h2>
<p>The Service is not intended for anyone under 18.</p>

<h2 class="h4 mt-4">10. Changes to this Policy</h2>
<p>We may update this Policy from time to time. When we make a material
change, we will increment the version and require you to re-accept the
updated Policy before continuing to use the Service.</p>

<h2 class="h4 mt-4">11. Contact</h2>
<p>Questions about this Policy? Email us at
<a href="mailto:rights@auditfile1983.com">rights@auditfile1983.com</a>.</p>
'''.strip()


def update_legal_copy(apps, schema_editor):
    LegalDocument = apps.get_model('accounts', 'LegalDocument')
    SiteSettings = apps.get_model('accounts', 'SiteSettings')

    LegalDocument.objects.update_or_create(
        doc_type='terms',
        defaults={
            'title': 'Terms of Service',
            'content': TERMS_HTML,
            'version': 'v1',
        },
    )
    LegalDocument.objects.update_or_create(
        doc_type='privacy',
        defaults={
            'title': 'Privacy Policy',
            'content': PRIVACY_HTML,
            'version': 'v1',
        },
    )

    # Nudge the brand name only if the singleton is still on the original
    # "File 1983" default. If you've already customized it in admin, leave
    # your override alone.
    settings_row = SiteSettings.objects.filter(pk=1).first()
    if settings_row:
        changed = False
        if settings_row.app_name == 'File 1983':
            settings_row.app_name = 'AuditFile 1983'
            changed = True
        if settings_row.header_app_name == 'File 1983':
            settings_row.header_app_name = 'AuditFile 1983'
            changed = True
        if changed:
            settings_row.save()


def noop(apps, schema_editor):
    """Reverse migration is a no-op — we don't restore the old copy."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_legal_acceptance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitesettings',
            name='app_name',
            field=models.CharField(default='AuditFile 1983', max_length=100),
        ),
        migrations.AlterField(
            model_name='sitesettings',
            name='header_app_name',
            field=models.CharField(default='AuditFile 1983', max_length=100),
        ),
        migrations.RunPython(update_legal_copy, noop),
    ]
