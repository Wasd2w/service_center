"""Views та форми для авторизації і управління профілем користувача.

Модуль реалізує:
- вхід до системи з автентифікацією
- вихід із сесії
- перегляд та оновлення профілю майстра
- зміну пароля з оновленням сесії (без повторного логіну)

Архітектурне рішення: форми визначені в цьому ж файлі (не у forms.py),
оскільки вони повністю специфічні для сторінок акаунту і не перевикористовуються
в інших модулях.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django import forms


class LoginForm(forms.Form):
    """Форма входу до системи сервісного центру.

    Attributes:
        username: Поле логіну з автофокусом.
        password: Поле пароля з прихованим введенням.
    """

    username = forms.CharField(
        label="Логін",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Введіть логін",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Введіть пароль",
            }
        ),
    )


class ProfileForm(forms.ModelForm):
    """Форма оновлення профілю майстра.

    Дозволяє змінити ім'я, прізвище та email.
    Логін та права доступу змінюються тільки через Django admin.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }


class PasswordChangeForm(forms.Form):
    """Форма зміни пароля з підтвердженням.

    Validates:
        - Поточний пароль повинен збігатися зі збереженим.
        - Два поля нового пароля мають бути ідентичними.

    Attributes:
        old_password: Поточний пароль для підтвердження особи.
        new_password1: Новий пароль.
        new_password2: Повторення нового пароля.
    """

    old_password = forms.CharField(
        label="Поточний пароль", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    new_password1 = forms.CharField(
        label="Новий пароль", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )
    new_password2 = forms.CharField(
        label="Повторіть новий пароль", widget=forms.PasswordInput(attrs={"class": "form-control"})
    )

    def clean(self):
        """Перевіряє що обидва поля нового пароля співпадають.

        Raises:
            ValidationError: Якщо new_password1 != new_password2.
        """
        d = super().clean()
        if d.get("new_password1") != d.get("new_password2"):
            raise forms.ValidationError("Паролі не збігаються.")
        return d


def login_view(request):
    """Обробляє вхід користувача до системи.

    GET: повертає форму входу. Якщо користувач вже авторизований —
    перенаправляє на дашборд.

    POST: автентифікує користувача. При успіху — перенаправляє на
    ``next`` параметр або дашборд. При невдачі — показує повідомлення
    про помилку і повертає форму.

    Args:
        request: Django HttpRequest об'єкт.

    Returns:
        HttpResponse зі шаблоном ``accounts/login.html`` або redirect.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request, username=form.cleaned_data["username"], password=form.cleaned_data["password"]
        )
        if user:
            login(request, user)
            return redirect(request.GET.get("next", "dashboard"))
        else:
            messages.error(request, "Невірний логін або пароль.")
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout_view(request):
    """Виконує вихід поточного користувача з системи.

    Очищає сесію та перенаправляє на сторінку входу.

    Args:
        request: Django HttpRequest об'єкт.

    Returns:
        Redirect на ``login`` URL.
    """
    logout(request)
    return redirect("login")


@login_required
def profile_view(request):
    """Відображає та оновлює профіль поточного майстра.

    Сторінка містить дві незалежні форми з різними action-кнопками:
    - ``update_profile`` — оновлення імені, прізвища, email
    - ``change_password`` — зміна пароля

    При зміні пароля викликає ``update_session_auth_hash`` щоб
    користувач не був розлогінений після зміни.

    Також відображає 5 останніх заявок майстра та кількість активних.

    Args:
        request: Django HttpRequest об'єкт.

    Returns:
        HttpResponse зі шаблоном ``accounts/profile.html``.
    """
    profile_form = ProfileForm(instance=request.user)
    password_form = PasswordChangeForm()

    if request.method == "POST":
        if "update_profile" in request.POST:
            profile_form = ProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "Профіль оновлено.")
                return redirect("profile")

        elif "change_password" in request.POST:
            password_form = PasswordChangeForm(request.POST)
            if password_form.is_valid():
                if request.user.check_password(password_form.cleaned_data["old_password"]):
                    request.user.set_password(password_form.cleaned_data["new_password1"])
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "Пароль змінено.")
                    return redirect("profile")
                else:
                    messages.error(request, "Поточний пароль невірний.")

    from apps.repairs.models import Repair

    my_repairs = Repair.objects.filter(master=request.user).order_by("-created_at")[:5]
    active_count = (
        Repair.objects.filter(master=request.user)
        .exclude(status__in=["done", "issued", "cancelled"])
        .count()
    )

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "my_repairs": my_repairs,
            "active_count": active_count,
        },
    )
