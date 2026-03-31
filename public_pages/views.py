from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from datetime import datetime, timedelta
from .models import CivilRightsPage, PageSection


def robots_txt(request):
    protocol = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "Disallow: /accounts/",
        "Disallow: /documents/",
        "",
        f"Sitemap: {protocol}://{host}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def cms_page(request, slug):
    page = get_object_or_404(CivilRightsPage, slug=slug, is_published=True)
    sections = page.sections.filter(is_visible=True).order_by('order')
    return render(request, 'public_pages/cms_page.html', {'page': page, 'sections': sections})


def landing_page(request):
    featured_articles = [
        {
            'title': 'Your Right to Record Police',
            'summary': 'The First Amendment protects your right to record police officers performing their duties in public. Learn what the courts have said and how to protect yourself.',
            'icon': 'bi-camera-video',
            'category': 'First Amendment',
            'url': 'public_pages:right_to_record',
        },
        {
            'title': 'Understanding Section 1983',
            'summary': "Section 1983 is the federal law that allows you to sue government officials who violate your constitutional rights. Here's how it works.",
            'icon': 'bi-journal-text',
            'category': 'Legal Basics',
            'url': 'public_pages:section_1983',
        },
        {
            'title': 'What to Do If Your Rights Are Violated',
            'summary': 'Step-by-step guide on documenting incidents, preserving evidence, and understanding your options when police or government officials violate your rights.',
            'icon': 'bi-shield-check',
            'category': 'Take Action',
            'url': 'public_pages:rights_violated',
        },
        {
            'title': 'First Amendment Auditors',
            'summary': 'Meet the everyday Americans who test and protect our constitutional rights through peaceful First Amendment audits.',
            'icon': 'bi-camera-video',
            'category': 'Freedom Fighters',
            'url': 'public_pages:first_amendment_auditors',
        },
    ]

    sample_news = [
        {'title': 'Federal Court Rules Citizens Have Right to Record Traffic Stops', 'source': 'ACLU', 'date': datetime.now() - timedelta(days=1), 'url': '#'},
        {'title': 'Supreme Court to Hear Qualified Immunity Case This Term', 'source': 'Reuters', 'date': datetime.now() - timedelta(days=2), 'url': '#'},
        {'title': 'New Body Camera Footage Requirements Take Effect in Three States', 'source': 'AP News', 'date': datetime.now() - timedelta(days=3), 'url': '#'},
        {'title': 'Civil Rights Groups Call for Police Accountability Reforms', 'source': 'NPR', 'date': datetime.now() - timedelta(days=4), 'url': '#'},
        {'title': 'First Amendment Audit Movement Grows Across America', 'source': 'Washington Post', 'date': datetime.now() - timedelta(days=5), 'url': '#'},
    ]

    key_rights = [
        {'amendment': '1st', 'title': 'Freedom of Speech & Press', 'description': 'You have the right to record police, attend public meetings, and speak freely on matters of public concern.', 'icon': 'bi-megaphone', 'url': 'public_pages:right_to_record'},
        {'amendment': '4th', 'title': 'Protection from Unreasonable Search', 'description': 'Police generally need a warrant to search you or your property. You can refuse consent to searches.', 'icon': 'bi-shield-lock', 'url': 'public_pages:fourth_amendment'},
        {'amendment': '5th', 'title': 'Right to Remain Silent', 'description': 'You cannot be forced to incriminate yourself. You have the right to remain silent during police encounters.', 'icon': 'bi-chat-square-dots', 'url': 'public_pages:fifth_amendment'},
        {'amendment': '14th', 'title': 'Equal Protection & Due Process', 'description': 'Government must treat you fairly and cannot discriminate. You have the right to due process of law.', 'icon': 'bi-bank', 'url': 'public_pages:section_1983'},
    ]

    resources = [
        {'name': 'ACLU - Know Your Rights', 'url': 'https://www.aclu.org/know-your-rights', 'description': 'Comprehensive guides on your constitutional rights in various situations.'},
        {'name': 'Flex Your Rights', 'url': 'https://www.flexyourrights.org/', 'description': 'Educational resources about asserting your rights during police encounters.'},
        {'name': 'Electronic Frontier Foundation', 'url': 'https://www.eff.org/', 'description': 'Digital rights and privacy protection in the modern age.'},
        {'name': 'Cornell Law - Section 1983', 'url': 'https://www.law.cornell.edu/uscode/text/42/1983', 'description': 'The actual text of 42 U.S.C. Section 1983.'},
    ]

    return render(request, 'public_pages/landing.html', {
        'featured_articles': featured_articles,
        'news_items': sample_news,
        'key_rights': key_rights,
        'resources': resources,
    })


def home(request):
    return landing_page(request)


def know_your_rights(request):
    return render(request, 'public_pages/know_your_rights.html')


def right_to_record(request):
    return render(request, 'public_pages/right_to_record.html')


def section_1983(request):
    return render(request, 'public_pages/section_1983.html')


def rights_violated(request):
    return render(request, 'public_pages/rights_violated.html')


def first_amendment_auditors(request):
    return render(request, 'public_pages/first_amendment_auditors.html')


def fourth_amendment(request):
    return render(request, 'public_pages/fourth_amendment.html')


def fifth_amendment(request):
    return render(request, 'public_pages/fifth_amendment.html')


def legal_page(request, doc_type):
    from accounts.models import LegalDocument
    try:
        doc = LegalDocument.objects.get(doc_type=doc_type)
    except LegalDocument.DoesNotExist:
        doc = None
    return render(request, f'legal/{doc_type}.html', {'doc': doc})
