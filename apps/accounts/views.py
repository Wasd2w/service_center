from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django import forms


class LoginForm(forms.Form):
    username = forms.CharField(
        label='Логін',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Введіть логін',
            'autofocus': True,
        }))
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Введіть пароль',
        }))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class PasswordChangeForm(forms.Form):
    old_password = forms.CharField(
        label='Поточний пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password1 = forms.CharField(
        label='Новий пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    new_password2 = forms.CharField(
        label='Повторіть новий пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean(self):
        d = super().clean()
        if d.get('new_password1') != d.get('new_password2'):
            raise forms.ValidationError('Паролі не збігаються.')
        return d


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, 'Невірний логін або пароль.')
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def profile_view(request):
    profile_form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm()

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, 'Профіль оновлено.')
                return redirect('profile')

        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(request.POST)
            if password_form.is_valid():
                if request.user.check_password(password_form.cleaned_data['old_password']):
                    request.user.set_password(password_form.cleaned_data['new_password1'])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, 'Пароль змінено.')
                    return redirect('profile')
                else:
                    messages.error(request, 'Поточний пароль невірний.')

    from apps.repairs.models import Repair
    my_repairs = Repair.objects.filter(master=request.user).order_by('-created_at')[:5]
    active_count = Repair.objects.filter(
        master=request.user
    ).exclude(status__in=['done', 'issued', 'cancelled']).count()

    return render(request, 'accounts/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'my_repairs': my_repairs,
        'active_count': active_count,
    })
