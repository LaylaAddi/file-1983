from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth import views as auth_views

from .forms import RegisterForm, LoginForm, ProfileForm, CustomPasswordResetForm, CustomSetPasswordForm
from .models import SiteSettings


def register(request):
    settings_obj = SiteSettings.get_solo()
    if not settings_obj.registration_open:
        messages.error(request, 'Registration is currently closed.')
        return redirect('accounts:login')

    if request.user.is_authenticated:
        return redirect('documents:list')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.get_full_name() or user.email}!')
            return redirect('documents:list')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    if request.user.is_authenticated:
        return redirect('documents:list')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'documents:list')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
    else:
        form = LoginForm(request)

    return render(request, 'accounts/login.html', {'form': form})


@require_POST
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('public_pages:home')


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    subscriptions = request.user.subscriptions.order_by('-created_at')
    packs = request.user.document_packs.order_by('-created_at')

    return render(request, 'accounts/profile.html', {
        'form': form,
        'subscriptions': subscriptions,
        'packs': packs,
    })
