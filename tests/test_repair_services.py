"""Тести сервісного шару — документують бізнес-логіку заявок.

Ці тести є «виконуваною специфікацією» для services.py.
Кожна назва тесту описує одне конкретне правило або поведінку.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from apps.repairs.models import Client, Device, Repair, Part
from apps.repairs.services import (
    check_unique_active_repair,
    validate_transition,
    apply_field_restrictions,
    update_repair,
    RepairTransitionError,
)


class TestCheckUniqueActiveRepair(TestCase):
    """Документує правило: одна активна заявка на пристрій."""

    def setUp(self):
        self.user = User.objects.create_user("m", password="p")
        self.client = Client.objects.create(first_name="А", last_name="Б", phone="+380991000001")
        self.device = Device.objects.create(
            client=self.client, device_type="laptop", brand="Apple", model="MacBook"
        )

    def test_no_error_when_device_is_none(self):
        """Якщо пристрій не вказаний — перевірка не виконується."""
        # Не повинно кидати виняток
        check_unique_active_repair(self.client, None)

    def test_no_error_when_no_active_repairs(self):
        """Якщо немає активних заявок для пристрою — все гаразд."""
        check_unique_active_repair(self.client, self.device)  # не повинно кидати

    def test_raises_when_active_repair_exists(self):
        """Якщо вже є активна заявка на пристрій — кидає ValidationError."""
        Repair.objects.create(
            client=self.client,
            device=self.device,
            problem_description="перша",
            status=Repair.STATUS_IN_PROGRESS,
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            check_unique_active_repair(self.client, self.device)

    def test_no_error_when_existing_repair_is_closed(self):
        """Якщо існуюча заявка закрита — можна створити нову."""
        Repair.objects.create(
            client=self.client,
            device=self.device,
            problem_description="закрита",
            status=Repair.STATUS_DONE,
            created_by=self.user,
        )
        check_unique_active_repair(self.client, self.device)  # не повинно кидати

    def test_exclude_pk_ignores_own_repair(self):
        """При редагуванні поточна заявка виключається з перевірки."""
        repair = Repair.objects.create(
            client=self.client,
            device=self.device,
            problem_description="редагована",
            status=Repair.STATUS_IN_PROGRESS,
            created_by=self.user,
        )
        # Редагування самої себе не повинно кидати помилку
        check_unique_active_repair(self.client, self.device, exclude_pk=repair.pk)


class TestValidateTransition(TestCase):
    """Документує матрицю дозволених переходів між статусами."""

    def setUp(self):
        self.user = User.objects.create_user("m2", password="p")
        self.client = Client.objects.create(first_name="В", last_name="Г", phone="+380991000002")
        self.repair = Repair.objects.create(
            client=self.client,
            problem_description="тест",
            status=Repair.STATUS_NEW,
            created_by=self.user,
        )

    def test_same_status_transition_is_always_allowed(self):
        """Перехід у той самий статус не є помилкою (ніяких змін)."""
        validate_transition(self.repair, Repair.STATUS_NEW)  # не кидає

    def test_new_to_diagnosed_is_allowed(self):
        """new → diagnosed: дозволено."""
        validate_transition(self.repair, Repair.STATUS_DIAGNOSED)

    def test_new_to_in_progress_is_forbidden(self):
        """new → in_progress: заборонено (треба спочатку діагностувати)."""
        with self.assertRaises(RepairTransitionError):
            validate_transition(self.repair, Repair.STATUS_IN_PROGRESS)

    def test_new_to_done_is_forbidden(self):
        """new → done: заборонено."""
        with self.assertRaises(RepairTransitionError):
            validate_transition(self.repair, Repair.STATUS_DONE)

    def test_done_to_issued_is_allowed(self):
        """done → issued: дозволено."""
        self.repair.status = Repair.STATUS_DONE
        validate_transition(self.repair, Repair.STATUS_ISSUED)

    def test_issued_to_anything_is_forbidden(self):
        """issued: кінцевий стан — жоден перехід неможливий."""
        self.repair.status = Repair.STATUS_ISSUED
        for status in [Repair.STATUS_NEW, Repair.STATUS_DONE, Repair.STATUS_CANCELLED]:
            with self.assertRaises(RepairTransitionError):
                validate_transition(self.repair, status)

    def test_in_progress_to_waiting_parts_forbidden_if_parts_exist(self):
        """in_progress → waiting_parts заборонено якщо запчастини вже є."""
        self.repair.status = Repair.STATUS_IN_PROGRESS
        self.repair.save()
        Part.objects.create(repair=self.repair, name="Термопаста", quantity=1, price=50)
        with self.assertRaises(RepairTransitionError):
            validate_transition(self.repair, Repair.STATUS_WAITING_PARTS)

    def test_waiting_parts_to_in_progress_forbidden_without_parts(self):
        """waiting_parts → in_progress заборонено без запчастин."""
        self.repair.status = Repair.STATUS_WAITING_PARTS
        self.repair.save()
        with self.assertRaises(RepairTransitionError):
            validate_transition(self.repair, Repair.STATUS_IN_PROGRESS)


class TestApplyFieldRestrictions(TestCase):
    """Документує які поля блокуються в залежності від статусу."""

    def setUp(self):
        self.user = User.objects.create_user("m3", password="p")
        self.client = Client.objects.create(first_name="Д", last_name="Е", phone="+380991000003")
        self.repair = Repair.objects.create(
            client=self.client,
            problem_description="тест",
            status=Repair.STATUS_NEW,
            created_by=self.user,
        )

    def test_diagnosis_removed_when_status_is_new(self):
        """При статусі 'new' поле diagnosis видаляється з даних."""
        data = {"status": Repair.STATUS_NEW, "diagnosis": "якийсь текст"}
        result = apply_field_restrictions(self.repair, data)
        self.assertNotIn("diagnosis", result)

    def test_work_done_removed_when_status_is_diagnosed(self):
        """При статусі 'diagnosed' поле work_done видаляється."""
        data = {"status": Repair.STATUS_DIAGNOSED, "work_done": "роботи"}
        result = apply_field_restrictions(self.repair, data)
        self.assertNotIn("work_done", result)

    def test_estimated_cost_removed_when_status_is_in_progress(self):
        """При 'in_progress' estimated_cost заблоковано (вартість вже зафіксована)."""
        data = {"status": Repair.STATUS_IN_PROGRESS, "estimated_cost": 500}
        result = apply_field_restrictions(self.repair, data)
        self.assertNotIn("estimated_cost", result)

    def test_work_done_kept_when_status_is_in_progress(self):
        """При 'in_progress' поле work_done залишається (дозволено редагувати)."""
        data = {"status": Repair.STATUS_IN_PROGRESS, "work_done": "замінено термопасту"}
        result = apply_field_restrictions(self.repair, data)
        self.assertIn("work_done", result)

    def test_diagnosis_kept_when_status_is_in_progress(self):
        """При 'in_progress' поле diagnosis залишається."""
        data = {"status": Repair.STATUS_IN_PROGRESS, "diagnosis": "перегрів"}
        result = apply_field_restrictions(self.repair, data)
        self.assertIn("diagnosis", result)


class TestUpdateRepair(TestCase):
    """Документує головну точку входу для оновлення заявок."""

    def setUp(self):
        self.user = User.objects.create_user("m4", password="p")
        self.client = Client.objects.create(first_name="Ж", last_name="З", phone="+380991000004")
        self.repair = Repair.objects.create(
            client=self.client,
            problem_description="тест",
            status=Repair.STATUS_NEW,
            created_by=self.user,
        )

    def test_valid_transition_updates_status(self):
        """Валідний перехід змінює статус заявки."""
        update_repair(self.repair, {"status": Repair.STATUS_DIAGNOSED}, self.user)
        self.repair.refresh_from_db()
        self.assertEqual(self.repair.status, Repair.STATUS_DIAGNOSED)

    def test_invalid_transition_raises_error(self):
        """Недозволений перехід кидає RepairTransitionError, заявка не змінюється."""
        with self.assertRaises(RepairTransitionError):
            update_repair(self.repair, {"status": Repair.STATUS_DONE}, self.user)
        self.repair.refresh_from_db()
        self.assertEqual(self.repair.status, Repair.STATUS_NEW)  # не змінилось

    def test_update_is_atomic_on_error(self):
        """При помилці транзакція відкочується — жодних часткових змін."""
        original_desc = self.repair.problem_description
        with self.assertRaises(RepairTransitionError):
            update_repair(
                self.repair,
                {"status": Repair.STATUS_ISSUED, "problem_description": "змінено"},
                self.user,
            )
        self.repair.refresh_from_db()
        self.assertEqual(self.repair.problem_description, original_desc)
