from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Repair



class RepairTransitionError(ValidationError):
    pass
def check_unique_active_repair(client, device, exclude_pk=None):

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
            f'Для цього пристрою вже існує активна заявка '
            f'{conflict.number} (статус: {conflict.get_status_display()}). '
            f'Спочатку завершіть або скасуйте попередню заявку.'
        )

def validate_transition(repair: Repair, new_status: str) -> None:

    current = repair.status

    if current == new_status:
        return

    allowed = repair.get_allowed_transitions()

    if new_status not in allowed:
        current_label = dict(Repair.STATUS_CHOICES).get(current, current)
        new_label     = dict(Repair.STATUS_CHOICES).get(new_status, new_status)
        raise RepairTransitionError(
            f'Перехід «{current_label}» → «{new_label}» заборонений. '
            f'Дозволені переходи: {_labels(allowed)}.'
        )

    has_parts = repair.parts.exists()

    if current == Repair.STATUS_IN_PROGRESS and new_status == Repair.STATUS_WAITING_PARTS:
        if has_parts:
            raise RepairTransitionError(
                'Запчастини вже додані до заявки. '
                'Немає потреби переходити в «Очікування запчастин» — '
                'переходьте одразу в «Виконано».'
            )

    if current == Repair.STATUS_WAITING_PARTS and new_status == Repair.STATUS_IN_PROGRESS:
        if not has_parts:
            raise RepairTransitionError(
                'Спочатку додайте запчастини перед поверненням у «В роботі».'
            )

    if current == Repair.STATUS_WAITING_PARTS and new_status == Repair.STATUS_DONE:
        if not has_parts:
            raise RepairTransitionError(
                'Не можна перейти у «Виконано» без жодної запчастини '
                'зі статусу «Очікування запчастин».'
            )


def _labels(status_keys):
    m = dict(Repair.STATUS_CHOICES)
    return ', '.join(f'«{m.get(k, k)}»' for k in status_keys) or '(немає)'


def apply_field_restrictions(repair: Repair, data: dict) -> dict:

    new_status = data.get('status', repair.status)
    cleaned = dict(data)

    if new_status == Repair.STATUS_NEW:
        cleaned.pop('diagnosis', None)

    if new_status not in Repair.WORK_DONE_EDITABLE_STATUSES:
        cleaned.pop('work_done', None)

    if new_status in Repair.COST_LOCKED_STATUSES:
        cleaned.pop('estimated_cost', None)

    return cleaned

@transaction.atomic
def update_repair(repair: Repair, data: dict, user) -> Repair:

    new_status = data.get('status', repair.status)

    validate_transition(repair, new_status)

    data = apply_field_restrictions(repair, data)

    for field, value in data.items():
        setattr(repair, field, value)

    repair.save()
    return repair
