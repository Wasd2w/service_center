from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Client(models.Model):
    first_name = models.CharField('Імʼя', max_length=100)
    last_name  = models.CharField('Прізвище', max_length=100)
    phone      = models.CharField('Телефон', max_length=20, unique=True)
    email      = models.EmailField('Email', blank=True)
    city       = models.CharField('Місто', max_length=100, blank=True)
    street     = models.CharField('Вулиця', max_length=150, blank=True)
    building   = models.CharField('Будинок / кв.', max_length=20, blank=True)
    created_at = models.DateTimeField('Дата реєстрації', auto_now_add=True)

    class Meta:
        verbose_name = 'Клієнт'
        verbose_name_plural = 'Клієнти'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.last_name} {self.first_name}'

    def get_full_name(self):
        return f'{self.last_name} {self.first_name}'

    def get_address(self):
        parts = [p for p in [self.city, self.street, self.building] if p]
        return ', '.join(parts) if parts else '—'

    def active_repairs_count(self):
        return self.repairs.exclude(status__in=['done', 'issued', 'cancelled']).count()


class Device(models.Model):
    DEVICE_TYPES = [
        ('laptop',  'Ноутбук'),
        ('phone',   'Телефон'),
        ('tablet',  'Планшет'),
        ('desktop', 'Компʼютер'),
        ('printer', 'Принтер'),
        ('tv',      'Телевізор'),
        ('other',   'Інше'),
    ]
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE,
        related_name='devices', verbose_name='Клієнт')
    device_type = models.CharField('Тип пристрою', max_length=20, choices=DEVICE_TYPES)
    brand = models.CharField('Бренд', max_length=100)
    model = models.CharField('Модель', max_length=100)
    serial_number = models.CharField('Серійний номер', max_length=100, blank=True)
    notes = models.TextField('Примітки', blank=True)

    class Meta:
        verbose_name = 'Пристрій'
        verbose_name_plural = 'Пристрої'

    def __str__(self):
        return f'{self.get_device_type_display()} {self.brand} {self.model}'


class Repair(models.Model):
    STATUS_NEW = 'new'
    STATUS_DIAGNOSED = 'diagnosed'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_WAITING_PARTS = 'waiting_parts'
    STATUS_DONE = 'done'
    STATUS_ISSUED = 'issued'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_NEW,           'Нова заявка'),
        (STATUS_DIAGNOSED,     'Діагностовано'),
        (STATUS_IN_PROGRESS,   'В роботі'),
        (STATUS_WAITING_PARTS, 'Очікування запчастин'),
        (STATUS_DONE,          'Виконано'),
        (STATUS_ISSUED,        'Видано'),
        (STATUS_CANCELLED,     'Скасовано'),
    ]

    PRIORITY_CHOICES = [
        ('low',    'Низький'),
        ('normal', 'Нормальний'),
        ('high',   'Високий'),
        ('urgent', 'Терміновий'),
    ]

    ACTIVE_STATUSES = [STATUS_NEW, STATUS_DIAGNOSED, STATUS_IN_PROGRESS, STATUS_WAITING_PARTS]
    CLOSED_STATUSES = [STATUS_DONE, STATUS_ISSUED, STATUS_CANCELLED]
    COST_LOCKED_STATUSES = [
        STATUS_IN_PROGRESS, STATUS_WAITING_PARTS,
        STATUS_DONE, STATUS_ISSUED, STATUS_CANCELLED]
    MASTER_REQUIRED_STATUSES = [
        STATUS_IN_PROGRESS, STATUS_WAITING_PARTS,
        STATUS_DONE, STATUS_ISSUED]

    DIAGNOSIS_EDITABLE_STATUSES = [STATUS_DIAGNOSED, STATUS_IN_PROGRESS, STATUS_WAITING_PARTS]
    WORK_DONE_EDITABLE_STATUSES = [STATUS_IN_PROGRESS, STATUS_DONE]

    STATUS_TRANSITIONS = {
        STATUS_NEW:           [STATUS_DIAGNOSED, STATUS_CANCELLED],
        STATUS_DIAGNOSED:     [STATUS_IN_PROGRESS, STATUS_WAITING_PARTS, STATUS_CANCELLED],
        STATUS_IN_PROGRESS:   [STATUS_WAITING_PARTS, STATUS_DONE, STATUS_CANCELLED],
        STATUS_WAITING_PARTS: [STATUS_IN_PROGRESS, STATUS_CANCELLED],
        STATUS_DONE:          [STATUS_ISSUED],
        STATUS_ISSUED:        [],
        STATUS_CANCELLED:     [],
    }

    number = models.CharField('Номер заявки', max_length=20, unique=True, blank=True)
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT,
        related_name='repairs', verbose_name='Клієнт')
    device = models.ForeignKey(
        Device, on_delete=models.PROTECT,
        related_name='repairs', verbose_name='Пристрій',
        null=True, blank=True)
    problem_description = models.TextField('Опис проблеми')
    diagnosis = models.TextField('Діагноз', blank=True)
    work_done = models.TextField('Виконані роботи', blank=True)
    master = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_repairs', verbose_name='Майстер')
    status = models.CharField(
        'Статус', max_length=20,
        choices=STATUS_CHOICES, default=STATUS_NEW)
    priority = models.CharField(
        'Пріоритет', max_length=10,
        choices=PRIORITY_CHOICES, default='normal')
    estimated_cost = models.DecimalField(
        'Орієнтовна вартість', max_digits=10,
        decimal_places=2, null=True, blank=True)
    labor_cost = models.DecimalField(
        'Вартість робіт', max_digits=10,
        decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField('Дата прийому', auto_now_add=True)
    updated_at = models.DateTimeField('Дата оновлення', auto_now=True)
    deadline = models.DateField('Дедлайн', null=True, blank=True)
    completed_at = models.DateTimeField('Дата завершення', null=True, blank=True)
    issued_at = models.DateTimeField('Дата видачі', null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_repairs', verbose_name='Прийнятий')

    class Meta:
        verbose_name = 'Заявка на ремонт'
        verbose_name_plural = 'Заявки на ремонт'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заявка №{self.number} — {self.client}'

    def save(self, *args, **kwargs):
        if not self.number:
            from django.db import transaction
            with transaction.atomic():
                last = Repair.objects.select_for_update().order_by('-id').first()
                next_id = (last.id + 1) if last else 1
                self.number = f'SC-{next_id:05d}'
        if self.status == self.STATUS_DONE and not self.completed_at:
            self.completed_at = timezone.now()
        if self.status == self.STATUS_ISSUED and not self.issued_at:
            self.issued_at = timezone.now()
        super().save(*args, **kwargs)

    def is_closed(self):
        return self.status in self.CLOSED_STATUSES

    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    def can_add_parts(self):
        return self.status in [
            self.STATUS_DIAGNOSED, self.STATUS_IN_PROGRESS, self.STATUS_WAITING_PARTS
        ]

    def is_cost_locked(self):
        return self.status in self.COST_LOCKED_STATUSES

    def is_diagnosis_editable(self):
        return self.status in self.DIAGNOSIS_EDITABLE_STATUSES

    def is_work_done_editable(self):
        return self.status in self.WORK_DONE_EDITABLE_STATUSES

    def get_allowed_transitions(self):
        return self.STATUS_TRANSITIONS.get(self.status, [])

    def parts_total(self):
        return sum(p.total() for p in self.parts.all())

    def total_cost(self):
        return self.parts_total() + (self.labor_cost or 0)

    def get_status_color(self):
        return {
            'new': 'primary', 'diagnosed': 'info', 'in_progress': 'warning',
            'waiting_parts': 'secondary', 'done': 'success',
            'issued': 'success', 'cancelled': 'danger',
        }.get(self.status, 'secondary')

    def get_priority_color(self):
        return {
            'low': 'secondary', 'normal': 'primary',
            'high': 'warning', 'urgent': 'danger',
        }.get(self.priority, 'secondary')

    def is_overdue(self):
        if self.deadline and not self.is_closed():
            return timezone.now().date() > self.deadline
        return False


class RepairComment(models.Model):
    repair = models.ForeignKey(Repair, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    text  = models.TextField('Коментар')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Коментар до {self.repair.number}'


class Part(models.Model):
    repair = models.ForeignKey(Repair, on_delete=models.CASCADE, related_name='parts')
    name = models.CharField('Назва запчастини', max_length=200)
    quantity = models.PositiveIntegerField('Кількість', default=1)
    price = models.DecimalField('Ціна', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Запчастина'
        verbose_name_plural = 'Запчастини'

    def __str__(self):
        return self.name

    def total(self):
        return self.quantity * self.price
