"""Тести моделі Repair — документують поведінку машини станів та методів.

Читаючи ці тести, розробник розуміє:
- Які переходи між статусами є дозволеними
- Коли автоматично встановлюється completed_at та issued_at
- Що повертають is_closed(), is_active(), can_add_parts()
- Як генерується унікальний номер заявки SC-XXXXX
"""

from django.test import TestCase
from django.contrib.auth.models import User
from apps.repairs.models import Client, Repair


class TestRepairStatusMethods(TestCase):
    """Документує методи перевірки статусу заявки."""

    def setUp(self):
        self.user = User.objects.create_user("master", password="pass")
        self.client_obj = Client.objects.create(
            first_name="Іван", last_name="Петренко", phone="+380991234567"
        )
        self.repair = Repair.objects.create(
            client=self.client_obj,
            problem_description="Не вмикається",
            created_by=self.user,
            status=Repair.STATUS_NEW,
        )

    # ── is_active() ───────────────────────────────────────────────────────────

    def test_new_repair_is_active(self):
        """Нова заявка вважається активною."""
        self.assertTrue(self.repair.is_active())

    def test_in_progress_repair_is_active(self):
        """Заявка 'в роботі' є активною."""
        self.repair.status = Repair.STATUS_IN_PROGRESS
        self.assertTrue(self.repair.is_active())

    def test_done_repair_is_not_active(self):
        """Виконана заявка не є активною."""
        self.repair.status = Repair.STATUS_DONE
        self.assertFalse(self.repair.is_active())

    # ── is_closed() ───────────────────────────────────────────────────────────

    def test_cancelled_repair_is_closed(self):
        """Скасована заявка є закритою."""
        self.repair.status = Repair.STATUS_CANCELLED
        self.assertTrue(self.repair.is_closed())

    def test_issued_repair_is_closed(self):
        """Видана заявка є закритою."""
        self.repair.status = Repair.STATUS_ISSUED
        self.assertTrue(self.repair.is_closed())

    def test_new_repair_is_not_closed(self):
        """Нова заявка не є закритою."""
        self.assertFalse(self.repair.is_closed())

    # ── can_add_parts() ───────────────────────────────────────────────────────

    def test_cannot_add_parts_to_new_repair(self):
        """До нової заявки не можна додавати запчастини."""
        self.assertFalse(self.repair.can_add_parts())

    def test_can_add_parts_when_diagnosed(self):
        """До діагностованої заявки можна додавати запчастини."""
        self.repair.status = Repair.STATUS_DIAGNOSED
        self.assertTrue(self.repair.can_add_parts())

    def test_cannot_add_parts_when_done(self):
        """До виконаної заявки не можна додавати запчастини."""
        self.repair.status = Repair.STATUS_DONE
        self.assertFalse(self.repair.can_add_parts())

    # ── get_allowed_transitions() ─────────────────────────────────────────────

    def test_new_repair_can_transition_to_diagnosed_or_cancelled(self):
        """З 'new' дозволено перейти тільки в 'diagnosed' або 'cancelled'."""
        allowed = self.repair.get_allowed_transitions()
        self.assertIn(Repair.STATUS_DIAGNOSED, allowed)
        self.assertIn(Repair.STATUS_CANCELLED, allowed)
        self.assertNotIn(Repair.STATUS_IN_PROGRESS, allowed)
        self.assertNotIn(Repair.STATUS_DONE, allowed)

    def test_issued_repair_has_no_allowed_transitions(self):
        """Видана заявка є кінцевим станом — немає дозволених переходів."""
        self.repair.status = Repair.STATUS_ISSUED
        self.assertEqual(self.repair.get_allowed_transitions(), [])

    def test_cancelled_repair_has_no_allowed_transitions(self):
        """Скасована заявка є кінцевим станом — немає дозволених переходів."""
        self.repair.status = Repair.STATUS_CANCELLED
        self.assertEqual(self.repair.get_allowed_transitions(), [])

    # ── is_overdue() ──────────────────────────────────────────────────────────

    def test_repair_without_deadline_is_not_overdue(self):
        """Заявка без дедлайну ніколи не є простроченою."""
        self.repair.deadline = None
        self.assertFalse(self.repair.is_overdue())

    def test_closed_repair_with_past_deadline_is_not_overdue(self):
        """Закрита заявка не вважається простроченою навіть якщо дедлайн минув."""
        from datetime import date, timedelta

        self.repair.deadline = date.today() - timedelta(days=5)
        self.repair.status = Repair.STATUS_DONE
        self.assertFalse(self.repair.is_overdue())


class TestRepairNumberGeneration(TestCase):
    """Документує автоматичну генерацію номера заявки."""

    def setUp(self):
        self.user = User.objects.create_user("master2", password="pass")
        self.client_obj = Client.objects.create(
            first_name="Марія", last_name="Іваненко", phone="+380501111111"
        )

    def test_number_generated_on_first_save(self):
        """Номер заявки автоматично генерується при першому збереженні."""
        repair = Repair.objects.create(
            client=self.client_obj,
            problem_description="Тест",
            created_by=self.user,
        )
        self.assertTrue(repair.number.startswith("SC-"))
        self.assertEqual(len(repair.number), 8)  # SC-00001

    def test_number_format_is_sc_with_five_digits(self):
        """Формат номера: SC-XXXXX де XXXXX — п'ятизначне число з нулями."""
        repair = Repair.objects.create(
            client=self.client_obj,
            problem_description="Тест формату",
            created_by=self.user,
        )

        self.assertRegex(repair.number, r"^SC-\d{5}$")

    def test_number_is_unique_for_each_repair(self):
        """Кожна заявка отримує унікальний номер."""
        r1 = Repair.objects.create(
            client=self.client_obj, problem_description="1", created_by=self.user
        )
        r2 = Repair.objects.create(
            client=self.client_obj, problem_description="2", created_by=self.user
        )
        self.assertNotEqual(r1.number, r2.number)


class TestClientMethods(TestCase):
    """Документує методи моделі Client."""

    def test_get_full_name_returns_last_then_first(self):
        """get_full_name() повертає 'Прізвище Ім'я'."""
        c = Client(first_name="Іван", last_name="Петренко")
        self.assertEqual(c.get_full_name(), "Петренко Іван")

    def test_get_address_joins_non_empty_parts(self):
        """get_address() об'єднує непорожні компоненти через кому."""
        c = Client(city="Тернопіль", street="вул. Шевченка", building="15")
        self.assertEqual(c.get_address(), "Тернопіль, вул. Шевченка, 15")

    def test_get_address_returns_dash_when_empty(self):
        """get_address() повертає '—' якщо адреса не вказана."""
        c = Client(city="", street="", building="")
        self.assertEqual(c.get_address(), "—")

    def test_get_address_skips_empty_parts(self):
        """get_address() пропускає порожні компоненти."""
        c = Client(city="Київ", street="", building="5")
        self.assertEqual(c.get_address(), "Київ, 5")
