from django import forms
from django.conf import settings as dj_settings
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a password'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm your password'}),
    )
    referral_code = forms.CharField(
        required=False,
        label='Referral Code (optional)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter referral code'}),
    )
    tos_accepted = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Terms of Service to create an account.'},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    privacy_accepted = forms.BooleanField(
        required=True,
        error_messages={'required': 'You must agree to the Privacy Policy to create an account.'},
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
        }

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        now = timezone.now()
        user.tos_accepted_at = now
        user.tos_accepted_version = getattr(dj_settings, 'TOS_VERSION', 'v1')
        user.privacy_accepted_at = now
        user.privacy_accepted_version = getattr(dj_settings, 'PRIVACY_VERSION', 'v1')
        if commit:
            user.save()
            ref_code = self.cleaned_data.get('referral_code', '').strip()
            if ref_code:
                referrer = self._resolve_referrer(ref_code)
                if referrer and referrer.id != user.id:
                    user.referred_by = referrer
                    user.save(update_fields=['referred_by'])
        return user

    def _resolve_referrer(self, ref_code):
        """
        Two-tier lookup so the same input field handles both the legacy
        per-user random referral_code AND the partner system's PromoCode.
        """
        from documents.models import PromoCode

        try:
            return User.objects.get(referral_code=ref_code)
        except User.DoesNotExist:
            pass

        promo = PromoCode.objects.filter(code__iexact=ref_code, is_active=True).first()
        if promo and promo.created_by_id:
            return promo.created_by
        return None


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com', 'autofocus': True}),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
    )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'zip_code')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. (555) 867-5309'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP code'}),
        }


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
