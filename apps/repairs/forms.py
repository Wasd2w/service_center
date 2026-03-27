import re
from datetime import date

from django import forms
from django.contrib.auth.models import User

from .models import Repair, Client, Device, RepairComment, Part
from .services import check_unique_active_repair


def only_letters(value, field_name):
    v = value.strip()
    if not v:
        raise forms.ValidationError(f"{field_name} не може бути порожнім.")
    if not all(c.isalpha() or c in " '-" for c in v):
        raise forms.ValidationError(
            f"{field_name} може містити лише літери, пробіл, апостроф або дефіс.")
    return v


def validate_serial(value):
    v = value.strip()
    if not v:
        return v
    if not re.match(r'^[A-Za-z0-9\-\/]+$', v):
        raise forms.ValidationError(
            "Серійний номер може містити лише латинські літери (A-Z), цифри, дефіс або /.")
    return v.upper()


def validate_brand_model(value, label):
    v = value.strip()
    if not v:
        raise forms.ValidationError(f"{label} не може бути порожнім.")
    if not re.match(r'^[A-Za-zА-Яа-яІіЄєЇїҐґ0-9\s\-\.\+\/]+$', v):
        raise forms.ValidationError(f"Поле «{label}» містить недопустимі символи.")
    return v


class ClientForm(forms.ModelForm):
    city = forms.CharField(
        label='Місто', required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'list': 'city-list',
            'placeholder': 'Починайте вводити місто...',
            'autocomplete': 'off',
        }))

    class Meta:
        model = Client
        fields = ['first_name', 'last_name', 'phone', 'email', 'city', 'street', 'building']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': "Введіть імʼя"}),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Введіть прізвище'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'phone-input',
                'placeholder': '+380XXXXXXXXX',
                'maxlength': '13'}),
            'email':    forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'email@example.com'}),
            'street':   forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'вул. Хрещатик'}),
            'building': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '12, кв. 34'}),
        }

    def clean_first_name(self):
        return only_letters(self.cleaned_data.get('first_name', ''), "Імʼя")

    def clean_last_name(self):
        return only_letters(self.cleaned_data.get('last_name', ''), "Прізвище")

    def clean_phone(self):
        value = self.cleaned_data.get('phone', '').strip()
        if not re.match(r'^\+380\d{9}$', value):
            raise forms.ValidationError(
                "Введіть номер у форматі +380XXXXXXXXX (9 цифр після +380).")
        return value

    def clean_city(self):
        return self.cleaned_data.get('city', '').strip()


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ['device_type', 'brand', 'model', 'serial_number', 'notes']
        widgets = {
            'device_type':   forms.Select(attrs={
                'class': 'form-select'}),
            'brand':         forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Samsung, Apple, HP...'}),
            'model':         forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Galaxy S21, MacBook Pro 14...'}),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Лише A-Z та 0-9, напр. SN12345ABC'}),
            'notes':         forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2}),
        }

    def clean_brand(self):
        return validate_brand_model(self.cleaned_data.get('brand', ''), 'Бренд')

    def clean_model(self):
        return validate_brand_model(self.cleaned_data.get('model', ''), 'Модель')

    def clean_serial_number(self):
        return validate_serial(self.cleaned_data.get('serial_number', ''))


class RepairForm(forms.ModelForm):

    class Meta:
        model = Repair
        fields = ['client', 'device', 'problem_description', 'priority', 'estimated_cost', 'deadline']
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'device': forms.Select(attrs={'class': 'form-select'}),
            'problem_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Опишіть несправність детально (мінімум 10 символів)...'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': '0.00', 'min': '0', 'step': '0.01'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].empty_label = None
        self.fields['client'].queryset = Client.objects.order_by('last_name', 'first_name')
        self.fields['device'].empty_label = None
        self.fields['device'].queryset = Device.objects.select_related('client').all()
        self.fields['device'].required = False

    def clean_problem_description(self):
        v = self.cleaned_data.get('problem_description', '').strip()
        if not v:
            raise forms.ValidationError("Опис проблеми не може бути порожнім.")
        if len(v) < 10:
            raise forms.ValidationError("Опис занадто короткий (мінімум 10 символів).")
        return v

    def clean_estimated_cost(self):
        v = self.cleaned_data.get('estimated_cost')
        if v is not None and v < 0:
            raise forms.ValidationError("Вартість не може бути відʼємною.")
        return v

    def clean_deadline(self):
        d = self.cleaned_data.get('deadline')
        if d and d < date.today():
            raise forms.ValidationError("Дедлайн не може бути в минулому.")
        return d

    def clean(self):
        cleaned = super().clean()
        device = cleaned.get('device')
        client = cleaned.get('client')

        if not client:
            return cleaned

        if device and device.client != client:
            self.add_error('device', 'Обраний пристрій не належить цьому клієнту.')
            return cleaned

        if device and client:
            try:
                check_unique_active_repair(
                    client=client,
                    device=device,
                    exclude_pk=self.instance.pk if self.instance else None,
                )
            except forms.ValidationError as exc:
                self.add_error('device', exc)

        return cleaned


class RepairUpdateForm(forms.ModelForm):

    MASTER_REQUIRED = Repair.MASTER_REQUIRED_STATUSES

    class Meta:
        model = Repair
        fields = ['status', 'priority', 'master', 'deadline',
                  'estimated_cost', 'diagnosis', 'work_done', 'labor_cost']
        widgets = {
            'status':   forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'master':   forms.Select(attrs={'class': 'form-select'}),
            'deadline': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Опишіть результат діагностики...'}),
            'work_done': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Перелічіть виконані роботи...'}),
            'labor_cost': forms.NumberInput(attrs={
                'class': 'form-control', 'min': '0', 'step': '0.01', 'placeholder': '0.00'}),
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        if self.current_user and not self.current_user.is_staff:
            self.fields['master'].queryset = User.objects.filter(
                id=self.current_user.id, is_active=True)
            self.fields['master'].empty_label = None
        else:
            self.fields['master'].queryset = User.objects.filter(is_active=True)
            self.fields['master'].empty_label = '— Не призначено —'

        self.fields['master'].label_from_instance = lambda u: (
            f'{u.last_name} {u.first_name}'.strip() or u.username
        )

        if not (self.instance and self.instance.pk):
            return

        current  = self.instance.status
        has_parts = self.instance.parts.exists()

        allowed_targets = list(Repair.STATUS_TRANSITIONS.get(current, []))

        if current == Repair.STATUS_IN_PROGRESS and Repair.STATUS_WAITING_PARTS in allowed_targets:
            if has_parts:
                allowed_targets.remove(Repair.STATUS_WAITING_PARTS)

        if current == Repair.STATUS_WAITING_PARTS:
            if has_parts:
                if Repair.STATUS_IN_PROGRESS not in allowed_targets:
                    allowed_targets.append(Repair.STATUS_IN_PROGRESS)
                if Repair.STATUS_DONE not in allowed_targets:
                    allowed_targets.append(Repair.STATUS_DONE)

        if current not in allowed_targets:
            allowed_targets.insert(0, current)

        self.fields['status'].choices = [
            (k, v) for k, v in Repair.STATUS_CHOICES if k in allowed_targets
        ]

        effective_status = (self.data.get('status') or current) if self.data else current

        if effective_status == Repair.STATUS_NEW:
            self.fields['diagnosis'].widget.attrs['disabled'] = True
            self.fields['diagnosis'].required = False

        if effective_status not in Repair.WORK_DONE_EDITABLE_STATUSES:
            self.fields['work_done'].widget.attrs['disabled'] = True
            self.fields['work_done'].required = False

        if self.instance.is_cost_locked():
            self.fields['estimated_cost'].widget.attrs['disabled'] = True
            self.fields['estimated_cost'].required = False

        if self.instance.deadline and 'deadline' not in (self.data or {}):
            self.initial['deadline'] = self.instance.deadline.strftime('%Y-%m-%d')

    def clean_estimated_cost(self):
        v = self.cleaned_data.get('estimated_cost')
        if self.instance and self.instance.is_cost_locked():
            return self.instance.estimated_cost
        if v is not None and v < 0:
            raise forms.ValidationError("Вартість не може бути відʼємною.")
        return v

    def clean_labor_cost(self):
        v = self.cleaned_data.get('labor_cost')
        if self.instance and self.instance.status in (Repair.STATUS_DONE, Repair.STATUS_ISSUED):
            return self.instance.labor_cost
        if v is not None and v < 0:
            raise forms.ValidationError("Вартість робіт не може бути відʼємною.")
        return v

    def clean_deadline(self):
        d = self.cleaned_data.get('deadline')
        if d and d < date.today():
            raise forms.ValidationError("Дедлайн не може бути в минулому.")
        return d

    def clean_diagnosis(self):
        inst = self.instance
        effective = self.cleaned_data.get('status') or (inst.status if inst else Repair.STATUS_NEW)
        if effective == Repair.STATUS_NEW:
            return inst.diagnosis if inst else ''
        return self.cleaned_data.get('diagnosis', '')

    def clean_work_done(self):
        inst = self.instance
        effective = self.cleaned_data.get('status') or (inst.status if inst else Repair.STATUS_NEW)
        if effective not in Repair.WORK_DONE_EDITABLE_STATUSES:
            return inst.work_done if inst else ''
        return self.cleaned_data.get('work_done', '')

    def clean(self):
        cleaned = super().clean()
        new_status = cleaned.get('status')
        master     = cleaned.get('master')
        inst       = self.instance
        cur_status = inst.status if inst else None

        if not new_status:
            return cleaned

        if inst and cur_status != new_status:
            from .services import validate_transition, RepairTransitionError
            try:
                validate_transition(inst, new_status)
            except RepairTransitionError as exc:
                self.add_error('status', exc)
                return cleaned

        if new_status in self.MASTER_REQUIRED and not master:
            if not (cur_status == Repair.STATUS_DONE and inst and inst.master):
                self.add_error(
                    'master',
                    f'Призначте майстра для статусу '
                    f'«{dict(Repair.STATUS_CHOICES).get(new_status, new_status)}».',
                )

        diagnosis = (cleaned.get('diagnosis') or '').strip()
        if not diagnosis and inst:
            diagnosis = (inst.diagnosis or '').strip()

        if new_status in (Repair.STATUS_DIAGNOSED, Repair.STATUS_IN_PROGRESS,
                          Repair.STATUS_WAITING_PARTS, Repair.STATUS_DONE):
            if not diagnosis:
                self.add_error('diagnosis', 'Вкажіть діагноз для цього статусу.')

        work_done = (cleaned.get('work_done') or '').strip()
        if not work_done and inst:
            work_done = (inst.work_done or '').strip()

        if new_status == Repair.STATUS_DONE and not work_done:
            self.add_error('work_done', 'Опишіть виконані роботи.')

        labor_cost = cleaned.get('labor_cost')
        if labor_cost is None and inst:
            labor_cost = inst.labor_cost

        if new_status == Repair.STATUS_DONE and labor_cost is None:
            self.add_error('labor_cost',
                'Вкажіть вартість робіт (введіть 0 якщо безкоштовно).')

        return cleaned


class RepairCommentForm(forms.ModelForm):
    class Meta:
        model = RepairComment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2, 'placeholder': 'Додати коментар...'}),
        }
        labels = {'text': ''}

    def clean_text(self):
        v = self.cleaned_data.get('text', '').strip()
        if not v:
            raise forms.ValidationError("Коментар не може бути порожнім.")
        return v


class PartForm(forms.ModelForm):
    class Meta:
        model = Part
        fields = ['name', 'quantity', 'price']
        widgets = {
            'name':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Назва запчастини'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'price':    forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }

    def clean_name(self):
        v = self.cleaned_data.get('name', '').strip()
        if not v:
            raise forms.ValidationError("Назва не може бути порожньою.")
        return v

    def clean_quantity(self):
        v = self.cleaned_data.get('quantity')
        if not v or v < 1:
            raise forms.ValidationError("Кількість — мінімум 1.")
        return v

    def clean_price(self):
        v = self.cleaned_data.get('price')
        if v is None or v <= 0:
            raise forms.ValidationError("Ціна повинна бути більше нуля.")
        return v


class RepairFilterForm(forms.Form):
    STATUS_CHOICES   = [('', 'Всі статуси')]    + Repair.STATUS_CHOICES
    PRIORITY_CHOICES = [('', 'Всі пріоритети')] + Repair.PRIORITY_CHOICES

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 'placeholder': 'Пошук за номером, клієнтом...'}))
    status = forms.ChoiceField(
        choices=STATUS_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES, required=False,
        widget=forms.Select(attrs={'class': 'form-select'}))
    master = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False, empty_label='Всі майстри',
        widget=forms.Select(attrs={'class': 'form-select'}))
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    date_to = forms.DateField(required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
