"""Моделі даних для системи управління ремонтами сервісного центру.

Модуль містить основні сутності:

- :class:`Client` — клієнт сервісного центру
- :class:`Device` — пристрій клієнта, що здається на ремонт
- :class:`Repair` — заявка на ремонт з машиною станів
- :class:`RepairComment` — внутрішній коментар до заявки
- :class:`Part` — запчастина використана при ремонті

Архітектурне рішення: моделі містять лише дані, валідацію полів
та прості обчислювальні property-методи. Вся бізнес-логіка
(машина станів, обмеження переходів) реалізована в ``services.py``.
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Client(models.Model):
    """Клієнт сервісного центру.

    Зберігає контактну інформацію та адресу клієнта.
    Є батьківською сутністю для Device та Repair.

    Attributes:
        first_name: Ім'я клієнта.
        last_name: Прізвище клієнта.
        phone: Унікальний номер телефону — основний ідентифікатор.
        email: Електронна пошта (необов'язкова).
        city: Місто проживання.
        street: Вулиця.
        building: Номер будинку / квартири.
        created_at: Дата та час першої реєстрації в системі.
    """

    first_name = models.CharField("Імʼя", max_length=100)
    last_name = models.CharField("Прізвище", max_length=100)
    phone = models.CharField("Телефон", max_length=20, unique=True)
    email = models.EmailField("Email", blank=True)
    city = models.CharField("Місто", max_length=100, blank=True)
    street = models.CharField("Вулиця", max_length=150, blank=True)
    building = models.CharField("Будинок / кв.", max_length=20, blank=True)
    created_at = models.DateTimeField("Дата реєстрації", auto_now_add=True)

    class Meta:
        verbose_name = "Клієнт"
        verbose_name_plural = "Клієнти"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    def get_full_name(self) -> str:
        """Повертає повне ім'я у форматі «Прізвище Ім'я».

        Returns:
            Рядок з прізвищем та іменем через пробіл.
        """
        return f"{self.last_name} {self.first_name}"

    def get_address(self) -> str:
        """Повертає відформатовану адресу клієнта.

        Об'єднує непорожні компоненти адреси (місто, вулицю, будинок)
        через кому. Якщо жоден компонент не заповнений — повертає «—».

        Returns:
            Рядок з адресою або '—' якщо адреса не вказана.

        Example:
            >>> client.city = 'Тернопіль'
            >>> client.street = 'вул. Шевченка'
            >>> client.building = '15'
            >>> client.get_address()
            'Тернопіль, вул. Шевченка, 15'
        """
        parts = [p for p in [self.city, self.street, self.building] if p]
        return ", ".join(parts) if parts else "—"

    def active_repairs_count(self) -> int:
        """Підраховує кількість активних заявок клієнта.

        Активними вважаються заявки зі статусами: new, diagnosed,
        in_progress, waiting_parts. Використовується в шаблонах
        для відображення завантаженості клієнта.

        Returns:
            Кількість незакритих заявок (int >= 0).
        """
        return self.repairs.exclude(status__in=["done", "issued", "cancelled"]).count()


class Device(models.Model):
    """Пристрій клієнта, що приймається на ремонт.

    Зберігає технічні характеристики пристрою та прив'язаний
    до конкретного клієнта. Один клієнт може мати кілька пристроїв.

    Attributes:
        client: Власник пристрою (ForeignKey → Client).
        device_type: Тип з фіксованого переліку DEVICE_TYPES.
        brand: Виробник (наприклад, 'Apple', 'Samsung').
        model: Назва моделі (наприклад, 'iPhone 13', 'Galaxy S21').
        serial_number: Серійний номер — необов'язковий, для точної ідентифікації.
        notes: Додаткові примітки про стан пристрою при прийомі.
    """

    DEVICE_TYPES = [
        ("laptop", "Ноутбук"),
        ("phone", "Телефон"),
        ("tablet", "Планшет"),
        ("desktop", "Компʼютер"),
        ("printer", "Принтер"),
        ("tv", "Телевізор"),
        ("other", "Інше"),
    ]
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="devices", verbose_name="Клієнт"
    )
    device_type = models.CharField("Тип пристрою", max_length=20, choices=DEVICE_TYPES)
    brand = models.CharField("Бренд", max_length=100)
    model = models.CharField("Модель", max_length=100)
    serial_number = models.CharField("Серійний номер", max_length=100, blank=True)
    notes = models.TextField("Примітки", blank=True)

    class Meta:
        verbose_name = "Пристрій"
        verbose_name_plural = "Пристрої"

    def __str__(self):
        return f"{self.get_device_type_display()} {self.brand} {self.model}"


class Repair(models.Model):
    """Заявка на ремонт — центральна сутність системи.

    Представляє повний цикл ремонту: від прийому пристрою
    до його видачі клієнту. Реалізує машину станів через
    ``STATUS_TRANSITIONS`` — словник дозволених переходів.

    Машина станів::

        new → diagnosed → in_progress → done → issued
          ↓         ↓            ↓
       cancelled  cancelled  waiting_parts → in_progress
                                    ↓
                                 cancelled

    Attributes:
        number: Унікальний номер заявки у форматі SC-00001.
            Генерується автоматично при першому збереженні.
        client: Клієнт — власник пристрою.
        device: Конкретний пристрій (може бути None якщо не вказано).
        problem_description: Опис несправності зі слів клієнта.
        diagnosis: Технічний діагноз майстра (заповнюється при diagnosed+).
        work_done: Опис виконаних робіт (заповнюється при in_progress+).
        master: Відповідальний майстер (User).
        status: Поточний статус із STATUS_CHOICES.
        priority: Пріоритет із PRIORITY_CHOICES.
        estimated_cost: Орієнтовна вартість (блокується після початку роботи).
        labor_cost: Фінальна вартість роботи майстра.
        created_at: Дата та час прийому заявки.
        deadline: Бажана дата завершення ремонту.
        completed_at: Фактична дата завершення (auto при status=done).
        issued_at: Дата видачі клієнту (auto при status=issued).
    """

    STATUS_NEW = "new"
    STATUS_DIAGNOSED = "diagnosed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_WAITING_PARTS = "waiting_parts"
    STATUS_DONE = "done"
    STATUS_ISSUED = "issued"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_NEW, "Нова заявка"),
        (STATUS_DIAGNOSED, "Діагностовано"),
        (STATUS_IN_PROGRESS, "В роботі"),
        (STATUS_WAITING_PARTS, "Очікування запчастин"),
        (STATUS_DONE, "Виконано"),
        (STATUS_ISSUED, "Видано"),
        (STATUS_CANCELLED, "Скасовано"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Низький"),
        ("normal", "Нормальний"),
        ("high", "Високий"),
        ("urgent", "Терміновий"),
    ]

    ACTIVE_STATUSES = [STATUS_NEW, STATUS_DIAGNOSED, STATUS_IN_PROGRESS, STATUS_WAITING_PARTS]
    CLOSED_STATUSES = [STATUS_DONE, STATUS_ISSUED, STATUS_CANCELLED]
    COST_LOCKED_STATUSES = [
        STATUS_IN_PROGRESS,
        STATUS_WAITING_PARTS,
        STATUS_DONE,
        STATUS_ISSUED,
        STATUS_CANCELLED,
    ]
    MASTER_REQUIRED_STATUSES = [
        STATUS_IN_PROGRESS,
        STATUS_WAITING_PARTS,
        STATUS_DONE,
        STATUS_ISSUED,
    ]

    DIAGNOSIS_EDITABLE_STATUSES = [STATUS_DIAGNOSED, STATUS_IN_PROGRESS, STATUS_WAITING_PARTS]
    WORK_DONE_EDITABLE_STATUSES = [STATUS_IN_PROGRESS, STATUS_DONE]

    STATUS_TRANSITIONS = {
        STATUS_NEW: [STATUS_DIAGNOSED, STATUS_CANCELLED],
        STATUS_DIAGNOSED: [STATUS_IN_PROGRESS, STATUS_WAITING_PARTS, STATUS_CANCELLED],
        STATUS_IN_PROGRESS: [STATUS_WAITING_PARTS, STATUS_DONE, STATUS_CANCELLED],
        STATUS_WAITING_PARTS: [STATUS_IN_PROGRESS, STATUS_CANCELLED],
        STATUS_DONE: [STATUS_ISSUED],
        STATUS_ISSUED: [],
        STATUS_CANCELLED: [],
    }

    number = models.CharField("Номер заявки", max_length=20, unique=True, blank=True)
    client = models.ForeignKey(
        Client, on_delete=models.PROTECT, related_name="repairs", verbose_name="Клієнт"
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.PROTECT,
        related_name="repairs",
        verbose_name="Пристрій",
        null=True,
        blank=True,
    )
    problem_description = models.TextField("Опис проблеми")
    diagnosis = models.TextField("Діагноз", blank=True)
    work_done = models.TextField("Виконані роботи", blank=True)
    master = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_repairs",
        verbose_name="Майстер",
    )
    status = models.CharField("Статус", max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW)
    priority = models.CharField(
        "Пріоритет", max_length=10, choices=PRIORITY_CHOICES, default="normal"
    )
    estimated_cost = models.DecimalField(
        "Орієнтовна вартість", max_digits=10, decimal_places=2, null=True, blank=True
    )
    labor_cost = models.DecimalField(
        "Вартість робіт", max_digits=10, decimal_places=2, null=True, blank=True
    )
    created_at = models.DateTimeField("Дата прийому", auto_now_add=True)
    updated_at = models.DateTimeField("Дата оновлення", auto_now=True)
    deadline = models.DateField("Дедлайн", null=True, blank=True)
    completed_at = models.DateTimeField("Дата завершення", null=True, blank=True)
    issued_at = models.DateTimeField("Дата видачі", null=True, blank=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_repairs",
        verbose_name="Прийнятий",
    )

    class Meta:
        verbose_name = "Заявка на ремонт"
        verbose_name_plural = "Заявки на ремонт"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заявка №{self.number} — {self.client}"

    def save(self, *args, **kwargs):
        """Зберігає заявку з автоматичною генерацією номера та дат.

        При першому збереженні генерує унікальний номер формату SC-00001
        використовуючи select_for_update() для безпечної конкурентності.
        Автоматично встановлює completed_at та issued_at при відповідних
        змінах статусу.
        """
        if not self.number:
            from django.db import transaction

            with transaction.atomic():
                last = Repair.objects.select_for_update().order_by("-id").first()
                next_id = (last.id + 1) if last else 1
                self.number = f"SC-{next_id:05d}"
        if self.status == self.STATUS_DONE and not self.completed_at:
            self.completed_at = timezone.now()
        if self.status == self.STATUS_ISSUED and not self.issued_at:
            self.issued_at = timezone.now()
        super().save(*args, **kwargs)

    def is_closed(self) -> bool:
        """Перевіряє чи заявка у закритому статусі.

        Returns:
            True якщо статус done, issued або cancelled.
        """
        return self.status in self.CLOSED_STATUSES

    def is_active(self) -> bool:
        """Перевіряє чи заявка у активному статусі.

        Returns:
            True якщо статус new, diagnosed, in_progress або waiting_parts.
        """
        return self.status in self.ACTIVE_STATUSES

    def can_add_parts(self) -> bool:
        """Перевіряє чи можна зараз додавати запчастини до заявки.

        Запчастини дозволено додавати лише коли ремонт вже розпочато
        (після діагностики). Це запобігає помилковому додаванню
        запчастин до нових або закритих заявок.

        Returns:
            True якщо статус diagnosed, in_progress або waiting_parts.
        """
        return self.status in [
            self.STATUS_DIAGNOSED,
            self.STATUS_IN_PROGRESS,
            self.STATUS_WAITING_PARTS,
        ]

    def is_cost_locked(self) -> bool:
        """Перевіряє чи заблоковано редагування орієнтовної вартості.

        Returns:
            True якщо статус in_progress або пізніший (крім cancelled).
        """
        return self.status in self.COST_LOCKED_STATUSES

    def is_diagnosis_editable(self) -> bool:
        """Перевіряє чи можна редагувати поле діагнозу.

        Returns:
            True якщо статус diagnosed, in_progress або waiting_parts.
        """
        return self.status in self.DIAGNOSIS_EDITABLE_STATUSES

    def is_work_done_editable(self) -> bool:
        """Перевіряє чи можна редагувати поле виконаних робіт.

        Returns:
            True якщо статус in_progress або done.
        """
        return self.status in self.WORK_DONE_EDITABLE_STATUSES

    def get_allowed_transitions(self) -> list:
        """Повертає список дозволених наступних статусів.

        Returns:
            Список рядкових ключів статусів або порожній список
            якщо поточний статус є кінцевим (issued, cancelled).
        """
        return self.STATUS_TRANSITIONS.get(self.status, [])

    def parts_total(self):
        """Обчислює загальну вартість всіх запчастин заявки.

        Returns:
            Decimal — сума (quantity * price) для всіх Part заявки.
        """
        return sum(p.total() for p in self.parts.all())

    def total_cost(self):
        """Обчислює повну вартість ремонту (запчастини + робота).

        Returns:
            Decimal — сума parts_total() та labor_cost (або 0 якщо не вказано).
        """
        return self.parts_total() + (self.labor_cost or 0)

    def get_status_color(self) -> str:
        """Повертає Bootstrap клас кольору для поточного статусу.

        Використовується в шаблонах для відображення кольорових бейджів.

        Returns:
            Рядок Bootstrap color класу (primary, info, warning, etc.).
        """
        return {
            "new": "primary",
            "diagnosed": "info",
            "in_progress": "warning",
            "waiting_parts": "secondary",
            "done": "success",
            "issued": "success",
            "cancelled": "danger",
        }.get(self.status, "secondary")

    def get_priority_color(self) -> str:
        """Повертає Bootstrap клас кольору для пріоритету заявки.

        Returns:
            Рядок Bootstrap color класу.
        """
        return {
            "low": "secondary",
            "normal": "primary",
            "high": "warning",
            "urgent": "danger",
        }.get(self.priority, "secondary")

    def is_overdue(self) -> bool:
        """Перевіряє чи прострочений дедлайн заявки.

        Заявка вважається простроченою якщо дедлайн вказаний,
        він у минулому, і заявка ще не закрита.

        Returns:
            True якщо дедлайн минув і заявка активна.
        """
        if self.deadline and not self.is_closed():
            return timezone.now().date() > self.deadline
        return False


class RepairComment(models.Model):
    """Внутрішній коментар до заявки на ремонт.

    Використовується персоналом для внутрішніх нотаток,
    спілкування між майстрами та адміністратором.
    Клієнти ці коментарі не бачать.

    Attributes:
        repair: Заявка до якої відноситься коментар.
        author: Автор коментаря (User, може бути None якщо видалений).
        text: Текст коментаря.
        created_at: Дата та час створення.
    """

    repair = models.ForeignKey(Repair, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    text = models.TextField("Коментар")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Коментар до {self.repair.number}"


class Part(models.Model):
    """Запчастина використана при ремонті.

    Кожна запчастина прив'язана до конкретної заявки.
    Вартість запчастин входить до загальної вартості ремонту.

    Attributes:
        repair: Заявка до якої відноситься ця запчастина.
        name: Назва запчастини (наприклад, 'Матриця 15.6 FHD IPS').
        quantity: Кількість одиниць (мінімум 1).
        price: Ціна за одиницю в гривнях.
    """

    repair = models.ForeignKey(Repair, on_delete=models.CASCADE, related_name="parts")
    name = models.CharField("Назва запчастини", max_length=200)
    quantity = models.PositiveIntegerField("Кількість", default=1)
    price = models.DecimalField("Ціна", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Запчастина"
        verbose_name_plural = "Запчастини"

    def __str__(self):
        return self.name

    def total(self):
        """Обчислює загальну вартість позиції (кількість × ціна).

        Returns:
            Decimal — добуток quantity та price.
        """
        return self.quantity * self.price
