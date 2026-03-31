from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def document_list(request):
    return render(request, 'documents/list.html')


@login_required
def document_create(request):
    return render(request, 'documents/list.html')
