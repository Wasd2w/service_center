"""Сервісний шар для управління заявками на ремонт.

Цей модуль реалізує бізнес-логіку, яка не належить до моделей:
- валідацію переходів між статусами заявки (машина станів)
- перевірку унікальності активних заявок на пристрій
- застосування обмежень полів залежно від статусу
- транзакційне оновлення заявки

Архітектурне рішення: вся бізнес-логіка зосереджена тут,
views лише делегують виклик і обробляють помилки.
"""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import Repair


class RepairTransitionError(ValidationError):
    """Помилка при спробі недозволеного переходу між статусами заявки.

    Наслідує ValidationError для сумісності з Django forms
    та можливості відображення через messages.error().
    """


def check_unique_active_repair(client, device, exclude_pk=None):
    """Перевіряє що для пристрою немає іншої активної заявки.

    Бізнес-правило: на один пристрій одночасно може існувати
    лише одна активна заявка (статуси: new, diagnosed,
    in_progress, waiting_parts). Це запобігає дублюванню
    та плутанині при паралельній роботі кількох майстрів.

    Args:
        client: Екземпляр моделі Client — власник пристрою.
        device: Екземпляр моделі Device або None. Якщо None —
            перевірка не виконується (пристрій не вказаний).
        exclude_pk: int або None — pk заявки яку треба виключити
            з перевірки (використовується при редагуванні).

    Raises:
        ValidationError: Якщо вже існує активна заявка на цей
            пристрій. Повідомлення містить номер конфліктної заявки
            та її поточний статус.

    Example:
        >>> check_unique_active_repair(client, device)
        # Нічого не повертає якщо конфлікту немає
        >>> check_unique_active_repair(client, device, exclude_pk=5)
        # Виключає заявку #5 з перевірки (при редагуванні)
    """
    if device is None:
        return

    qs = Repair.objects.filter(
        client=client,
        device=device,
        status__in=Repair.ACTIVE_STATUSES,
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    conflict = qs.first()
    if conflict:
        raise ValidationError(
            f"Для цього пристрою вже існує активна заявка "
            f"{conflict.number} (статус: {conflict.get_status_display()}). "
            f"Спочатку завершіть або скасуйте попередню заявку."
        )


def validate_transition(repair: Repair, new_status: str) -> None:
    """Перевіряє допустимість переходу між статусами заявки.

    Реалізує машину станів, визначену в ``Repair.STATUS_TRANSITIONS``.
    Окрім базової перевірки матриці переходів, застосовує додаткові
    бізнес-правила для специфічних переходів.

    Допустимі переходи:
        - new → diagnosed, cancelled
        - diagnosed → in_progress, waiting_parts, cancelled
        - in_progress → waiting_parts, done, cancelled
        - waiting_parts → in_progress, cancelled
        - done → issued
        - issued → (немає)
        - cancelled → (немає)

    Додаткові бізнес-правила:
        - in_progress → waiting_parts заборонено якщо запчастини вже додані
        - waiting_parts → in_progress вимагає наявності хоча б однієї запчастини
        - waiting_parts → done вимагає наявності хоча б однієї запчастини

    Args:
        repair: Поточна заявка на ремонт.
        new_status: Рядок нового статусу (одна зі значень STATUS_CHOICES).

    Raises:
        RepairTransitionError: Якщо перехід не дозволений матрицею
            або порушує бізнес-правила. Повідомлення пояснює причину
            та показує дозволені переходи.
    """
    current = repair.status

    if current == new_status:
        return

    allowed = repair.get_allowed_transitions()

    if new_status not in allowed:
        current_label = dict(Repair.STATUS_CHOICES).get(current, current)
        new_label = dict(Repair.STATUS_CHOICES).get(new_status, new_status)
        raise RepairTransitionError(
            f"Перехід «{current_label}» → «{new_label}» заборонений. "
            f"Дозволені переходи: {_labels(allowed)}."
        )

    has_parts = repair.parts.exists()

    if current == Repair.STATUS_IN_PROGRESS and new_status == Repair.STATUS_WAITING_PARTS:
        if has_parts:
            raise RepairTransitionError(
                "Запчастини вже додані до заявки. "
                "Немає потреби переходити в «Очікування запчастин» — "
                "переходьте одразу в «Виконано»."
            )

    if current == Repair.STATUS_WAITING_PARTS and new_status == Repair.STATUS_IN_PROGRESS:
        if not has_parts:
            raise RepairTransitionError(
                "Спочатку додайте запчастини перед поверненням у «В роботі»."
            )

    if current == Repair.STATUS_WAITING_PARTS and new_status == Repair.STATUS_DONE:
        if not has_parts:
            raise RepairTransitionError(
                "Не можна перейти у «Виконано» без жодної запчастини "
                "зі статусу «Очікування запчастин»."
            )


def _labels(status_keys):
    """Перетворює список ключів статусів у читабельний рядок.

    Допоміжна (приватна) функція для формування зрозумілих
    повідомлень про дозволені переходи.

    Args:
        status_keys: Список рядкових ключів статусів.

    Returns:
        Рядок виду «Виконано», «Видано» або '(немає)' якщо список порожній.
    """
    m = dict(Repair.STATUS_CHOICES)
    return ", ".join(f"«{m.get(k, k)}»" for k in status_keys) or "(немає)"


def apply_field_restrictions(repair: Repair, data: dict) -> dict:
    """Очищає поля що не можна редагувати в поточному/новому статусі.

    Різні статуси дозволяють редагувати різні поля. Ця функція
    видаляє з dict-у значення полів, зміна яких заборонена,
    запобігаючи несанкціонованому редагуванню через пряме POST.

    Правила обмежень:
        - diagnosis: тільки для diagnosed, in_progress, waiting_parts
        - work_done: тільки для in_progress, done
        - estimated_cost: заблоковано для in_progress, waiting_parts, done, issued, cancelled

    Args:
        repair: Поточна заявка (для визначення context'у).
        data: Словник даних форми (cleaned_data).

    Returns:
        Новий словник без заблокованих полів.

    Example:
        >>> data = {'status': 'new', 'diagnosis': 'текст', 'work_done': 'щось'}
        >>> clean = apply_field_restrictions(repair, data)
        >>> 'diagnosis' in clean
        False  # diagnosis недоступне при статусі 'new'
    """
    new_status = data.get("status", repair.status)
    cleaned = dict(data)

    if new_status == Repair.STATUS_NEW:
        cleaned.pop("diagnosis", None)

    if new_status not in Repair.WORK_DONE_EDITABLE_STATUSES:
        cleaned.pop("work_done", None)

    if new_status in Repair.COST_LOCKED_STATUSES:
        cleaned.pop("estimated_cost", None)

    return cleaned


@transaction.atomic
def update_repair(repair: Repair, data: dict, user) -> Repair:
    """Оновлює заявку на ремонт з валідацією всіх бізнес-правил.

    Головна точка входу для зміни заявки. Виконує в одній транзакції:
    1. Валідацію переходу статусу (validate_transition)
    2. Очищення заблокованих полів (apply_field_restrictions)
    3. Застосування нових значень через setattr
    4. Збереження (Repair.save() автоматично встановлює completed_at/issued_at)

    Args:
        repair: Існуюча заявка яку треба оновити.
        data: Словник нових значень полів (зазвичай form.cleaned_data).
        user: Поточний авторизований користувач (для аудиту).

    Returns:
        Оновлений екземпляр Repair.

    Raises:
        RepairTransitionError: Якщо новий статус недозволений.

    Example:
        >>> update_repair(repair, {'status': 'done', 'labor_cost': 500}, request.user)
    """
    new_status = data.get("status", repair.status)
    validate_transition(repair, new_status)
    data = apply_field_restrictions(repair, data)
    for field, value in data.items():
        setattr(repair, field, value)
    repair.save()
    return repair
