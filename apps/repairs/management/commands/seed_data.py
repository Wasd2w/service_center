import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.repairs.models import Client, Device, Repair, RepairComment, Part


PROBLEMS = [
    "Не вмикається, чорний екран після падіння",
    "Не заряджається акумулятор, індикатор не горить",
    "Зламана клавіатура, не реагує кілька клавіш",
    "Перегрівається та вимикається під навантаженням",
    "Не підключається до Wi-Fi, видає помилку",
    "Тріснуте скло дисплея, є мертві пікселі",
    "Повільна робота, постійно гальмує",
    "Не розпізнає SIM-картку",
    "Не працює динамік, немає звуку",
    "Вода потрапила всередину, є сліди окислення",
    "Не завантажується операційна система, BSOD",
    "Зламаний роз'єм зарядки",
    "Не працює камера, видає чорне зображення",
    "Вірусне зараження, потрібна чистка та переустановка",
    "Принтер не друкує, засмічені картриджі",
]

DIAGNOSES = [
    "Несправний контролер живлення, потребує заміни",
    "Акумулятор вийшов з ладу (ємність 12%), потрібна заміна",
    "Фізичне пошкодження клавіатурного модуля",
    "Засмічена система охолодження, потрібна чистка та термопаста",
    "Несправний мережевий модуль",
    "Пошкоджено матрицю та тачскрін, потрібна заміна",
    "Замість жорсткого диска рекомендується SSD, чистка Windows",
    "Несправний слот SIM-картки, потрібна пайка",
    "Обрив в ланцюгу динаміка, потрібне паяння",
    "Окислення на материнській платі, потрібне промивання спиртом",
]

WORK_DONE = [
    "Замінено контролер живлення, протестовано",
    "Встановлено новий акумулятор 4500 mAh",
    "Замінено клавіатурний модуль",
    "Очищено від пилу, нанесено термопасту Noctua NT-H1",
    "Замінено Wi-Fi модуль",
    "Встановлено новий дисплейний модуль",
    "Встановлено SSD 512GB, оновлено Windows",
    "Виконано пайку слота SIM",
    "Замінено динамік",
    "Промито плату, відновлено контакти",
]


class Command(BaseCommand):
    help = 'Заповнити базу тестовими даними'

    def handle(self, *args, i=None, **kwargs):
        self.stdout.write('Створення користувачів...')

        admin, _ = User.objects.get_or_create(username='admin')
        admin.set_password('admin123')
        admin.is_staff = True
        admin.is_superuser = True
        admin.first_name = 'Адміністратор'
        admin.last_name = 'Системи'
        admin.save()

        masters = []
        master_data = [
            ('master1', 'Іван', 'Коваленко', 'master123'),
            ('master2', 'Олена', 'Петренко', 'master123'),
            ('master3', 'Микола', 'Сидоренко', 'master123'),
        ]
        for username, first, last, pwd in master_data:
            u, _ = User.objects.get_or_create(username=username)
            u.set_password(pwd)
            u.first_name = first
            u.last_name = last
            u.save()
            masters.append(u)

        self.stdout.write('Створення клієнтів...')
        client_data = [
            ('Олександр', 'Шевченко', '+380501234567', 'shevchenko@gmail.com'),
            ('Марія', 'Бондаренко', '+380672345678', 'maria.b@ukr.net'),
            ('Петро', 'Мельник', '+380933456789', ''),
            ('Наталія', 'Ткаченко', '+380504567890', 'natalia@outlook.com'),
            ('Сергій', 'Кравченко', '+380675678901', ''),
            ('Оксана', 'Лисенко', '+380936789012', 'oksana.l@gmail.com'),
            ('Василь', 'Гриценко', '+380507890123', ''),
            ('Ірина', 'Мороз', '+380678901234', 'irina.m@ukr.net'),
            ('Андрій', 'Савченко', '+380939012345', ''),
            ('Тетяна', 'Руденко', '+380500123456', 'tetyana@gmail.com'),
            ('Дмитро', 'Павленко', '+380671234560', ''),
            ('Людмила', 'Захаренко', '+380932345671', 'ludmyla@ukr.net'),
        ]

        clients = []
        for first, last, phone, email in client_data:
            c, _ = Client.objects.get_or_create(
                phone=phone,
                defaults={'first_name': first, 'last_name': last, 'email': email}
            )
            clients.append(c)

        self.stdout.write('Створення пристроїв...')
        device_data = [
            ('laptop', 'Lenovo', 'ThinkPad X1 Carbon'),
            ('phone', 'Samsung', 'Galaxy S22'),
            ('laptop', 'Apple', 'MacBook Pro 14'),
            ('phone', 'Apple', 'iPhone 13'),
            ('tablet', 'Apple', 'iPad Air 5'),
            ('desktop', 'HP', 'EliteDesk 800'),
            ('printer', 'Canon', 'PIXMA MG3640'),
            ('phone', 'Xiaomi', 'Redmi Note 11'),
            ('laptop', 'ASUS', 'VivoBook 15'),
            ('tv', 'Samsung', 'QLED 55"'),
        ]

        devices = []
        for _i, (dtype, brand, model) in enumerate(device_data):
            client = clients[i % len(clients)]
            d, _ = Device.objects.get_or_create(
                client=client, brand=brand, model=model,
                defaults={'device_type': dtype}
            )
            devices.append(d)

        self.stdout.write('Створення заявок...')
        statuses = [
            'new', 'diagnosed', 'in_progress', 'waiting_parts',
            'done', 'issued', 'cancelled',
        ]
        priorities = ['low', 'normal', 'normal', 'high', 'urgent']

        for i in range(40):
            client = random.choice(clients)
            device = random.choice([d for d in devices if d.client == client] or devices)
            status = random.choice(statuses)
            priority = random.choice(priorities)
            days_ago = random.randint(0, 90)
            created = timezone.now() - timedelta(days=days_ago)

            repair = Repair(
                client=client,
                device=device,
                problem_description=random.choice(PROBLEMS),
                status=status,
                priority=priority,
                master=random.choice(masters + [None]),
                created_by=admin,
                estimated_cost=random.choice([500, 800, 1200, 1500, 2000, 2500, 3000]),
                created_at=created,
            )

            if status in ['done', 'issued']:
                repair.diagnosis = random.choice(DIAGNOSES)
                repair.work_done = random.choice(WORK_DONE)
                repair.labor_cost = random.choice([300, 500, 800, 1000, 1500])
                repair.completed_at = created + timedelta(days=random.randint(1, 5))

            if random.random() > 0.5:
                repair.deadline = (created + timedelta(days=random.randint(3, 14))).date()

            repair.save()

            if status in ['done', 'issued', 'in_progress'] and random.random() > 0.4:
                parts_list = [
                    ('Акумулятор', 1, random.randint(400, 1200)),
                    ('Дисплейний модуль', 1, random.randint(800, 2500)),
                    ('Термопаста', 1, 80),
                    ('Чистка від пилу', 1, 200),
                    ('SSD 256GB', 1, 1200),
                    ('Оперативна пам\'ять 8GB', 1, 600),
                ]
                for name, qty, price in random.sample(parts_list, random.randint(1, 2)):
                    Part.objects.create(repair=repair, name=name, quantity=qty, price=price)

            if random.random() > 0.6:
                RepairComment.objects.create(
                    repair=repair,
                    author=random.choice(masters),
                    text=random.choice([
                        'Запчастину замовлено, очікуємо 3-5 днів',
                        'Клієнт повідомлений про готовність',
                        'Потрібна додаткова діагностика материнської плати',
                        'Ремонт виконано, перевірено всі функції',
                        'Клієнт погодився на вартість ремонту',
                        'Пристрій готовий до видачі',
                    ])
                )

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Готово!\n'
            f'   Користувачів: {User.objects.count()}\n'
            f'   Клієнтів: {Client.objects.count()}\n'
            f'   Пристроїв: {Device.objects.count()}\n'
            f'   Заявок: {Repair.objects.count()}\n\n'
            f'   Вхід: admin / admin123\n'
            f'         master1 / master123\n'
        ))
