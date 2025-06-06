#!/usr/bin/env python3
"""
Скрипт для инициализации проекта с тестовыми данными
"""

from app import app
from models import db, User, Department, Vacancy, Test, Application, TestResult, CommissionVote
from datetime import datetime, timedelta
import json
import random

# Константы с данными пользователей
AUES_DEPARTMENTS = [
    "Кафедра автоматизации и управления (АУ)",
    "Кафедра IT-инженерии и искусственного интеллекта (ITЕ)",
    "Кафедра кибербезопасности (КБ)",
    "Кафедра теплоэнергетики и физики (ТЭ и Ф)",
    "Кафедра электроэнергетики (ЭЭ)",
    "Кафедра энергообеспечения, электропривода и электротехники (ЭОЭП и ЭТ)",
    "Кафедра электроснабжения и возобновляемых источников энергии (ЭВИЭ)",
    "Кафедра экологии и менеджмента в инженерии (ЭМИ)",
    "Кафедра телекоммуникационной инженерии (ТКИ)",
    "Кафедра космической инженерии (КИ)",
    "Кафедра электронной инженерии (ЭИ)",
    "Кафедра языков",
    "Кафедра социальных дисциплин (СД)",
    "Кафедра математики"
]

AUES_HR_USERS = [
    {
        'email': 'hr@aues.kz',
        'first_name': 'Алия',
        'last_name': 'Нурланова',
        'middle_name': 'Серикбаевна'
    },
    {
        'email': 'hr.recruitment@aues.kz',
        'first_name': 'Дана',
        'last_name': 'Жанибекова',
        'middle_name': 'Мухтаровна'
    },
    {
        'email': 'hr.management@aues.kz',
        'first_name': 'Гульнара',
        'last_name': 'Ахметова',
        'middle_name': 'Бакытжановна'
    }
]

AUES_DEPARTMENT_HEADS = [
    {
        'email': 'abzhanova@aues.kz',
        'first_name': 'Лауласын',
        'last_name': 'Абжанова',
        'middle_name': 'Косылгановна',
        'dept_name': 'Кафедра автоматизации и управления (АУ)'
    },
    {
        'email': 'utegenova@aues.kz',
        'first_name': 'Анар',
        'last_name': 'Утегенова',
        'middle_name': 'Урантаевна',
        'dept_name': 'Кафедра IT-инженерии и искусственного интеллекта (ITЕ)'
    },
    {
        'email': 'begimbaeva@aues.kz',
        'first_name': 'Енлик',
        'last_name': 'Бегимбаева',
        'middle_name': 'Ериковна',
        'dept_name': 'Кафедра кибербезопасности (КБ)'
    },
    {
        'email': 'korobkov@aues.kz',
        'first_name': 'Максим',
        'last_name': 'Коробков',
        'middle_name': 'Сергеевич',
        'dept_name': 'Кафедра теплоэнергетики и физики (ТЭ и Ф)'
    },
    {
        'email': 'uteshkalieva@aues.kz',
        'first_name': 'Ляззат',
        'last_name': 'Утешкалиева',
        'middle_name': 'Шынбулатовна',
        'dept_name': 'Кафедра электроэнергетики (ЭЭ)'
    },
    {
        'email': 'shynybay@aues.kz',
        'first_name': 'Жандос',
        'last_name': 'Шыныбай',
        'middle_name': 'Сапарғалиұлы',
        'dept_name': 'Кафедра энергообеспечения, электропривода и электротехники (ЭОЭП и ЭТ)'
    },
    {
        'email': 'tergemes@aues.kz',
        'first_name': 'Қажыбек',
        'last_name': 'Тергемес',
        'middle_name': 'Тілеуғалиұлы',
        'dept_name': 'Кафедра электроснабжения и возобновляемых источников энергии (ЭВИЭ)'
    },
    {
        'email': 'abikenova@aues.kz',
        'first_name': 'Асель',
        'last_name': 'Абикенова',
        'middle_name': 'Амангельдиевна',
        'dept_name': 'Кафедра экологии и менеджмента в инженерии (ЭМИ)'
    },
    {
        'email': 'kadylbekkyzy@aues.kz',
        'first_name': 'Эльвира',
        'last_name': 'Қадылбекқызы',
        'middle_name': '',
        'dept_name': 'Кафедра телекоммуникационной инженерии (ТКИ)'
    },
    {
        'email': 'tolendyuly@aues.kz',
        'first_name': 'Санат',
        'last_name': 'Төлендіұлы',
        'middle_name': '',
        'dept_name': 'Кафедра космической инженерии (КИ)'
    },
    {
        'email': 'orazalieva@aues.kz',
        'first_name': 'Сандугаш',
        'last_name': 'Оразалиева',
        'middle_name': 'Кудайбергеновна',
        'dept_name': 'Кафедра электронной инженерии (ЭИ)'
    },
    {
        'email': 'tuleup@aues.kz',
        'first_name': 'Мейримкул',
        'last_name': 'Тулеуп',
        'middle_name': 'Мухамедияровна',
        'dept_name': 'Кафедра языков'
    },
    {
        'email': 'kabdushev@aues.kz',
        'first_name': 'Булат',
        'last_name': 'Кабдушев',
        'middle_name': 'Жоламанович',
        'dept_name': 'Кафедра социальных дисциплин (СД)'
    },
    {
        'email': 'baysalova@aues.kz',
        'first_name': 'Маншук',
        'last_name': 'Байсалова',
        'middle_name': 'Жумамуратовна',
        'dept_name': 'Кафедра математики'
    }
]

CANDIDATES_DATA = [
    {
        'email': 'candidate1@example.com',
        'first_name': 'Алексей',
        'last_name': 'Морозов',
        'middle_name': 'Дмитриевич'
    },
    {
        'email': 'candidate2@example.com',
        'first_name': 'Мария',
        'last_name': 'Волкова',
        'middle_name': 'Андреевна'
    },
    {
        'email': 'candidate3@example.com',
        'first_name': 'Дмитрий',
        'last_name': 'Козлов',
        'middle_name': 'Сергеевич'
    }
]

# Константы с тестовыми данными
PROGRAMMING_TEST_QUESTIONS = [
    {
        'question': 'Какой язык программирования используется для веб-разработки на стороне сервера?',
        'options': ['HTML', 'CSS', 'JavaScript', 'Python'],
        'correct': 3
    },
    {
        'question': 'Что означает аббревиатура API?',
        'options': ['Application Programming Interface', 'Automated Program Integration', 'Advanced Programming Implementation', 'Application Process Integration'],
        'correct': 0
    },
    {
        'question': 'Какая из следующих структур данных использует принцип LIFO?',
        'options': ['Очередь', 'Стек', 'Массив', 'Список'],
        'correct': 1
    },
    {
        'question': 'Что такое SQL?',
        'options': ['Язык программирования', 'База данных', 'Язык структурированных запросов', 'Веб-фреймворк'],
        'correct': 2
    },
    {
        'question': 'Какой HTTP метод используется для создания новых ресурсов?',
        'options': ['GET', 'POST', 'PUT', 'DELETE'],
        'correct': 1
    },
    {
        'question': 'Что такое алгоритм сортировки пузырьком?',
        'options': ['Сравнивает соседние элементы и меняет их местами', 'Делит массив пополам', 'Ищет минимальный элемент', 'Использует рекурсию'],
        'correct': 0
    },
    {
        'question': 'Какая временная сложность у бинарного поиска?',
        'options': ['O(n)', 'O(log n)', 'O(n²)', 'O(1)'],
        'correct': 1
    },
    {
        'question': 'Что такое ООП?',
        'options': ['Объектно-ориентированное программирование', 'Операционная оптимизация программ', 'Основы обработки процессов', 'Открытая организация проектов'],
        'correct': 0
    },
    {
        'question': 'Какой принцип ООП обеспечивает сокрытие деталей реализации?',
        'options': ['Наследование', 'Полиморфизм', 'Инкапсуляция', 'Абстракция'],
        'correct': 2
    },
    {
        'question': 'Что такое Git?',
        'options': ['Текстовый редактор', 'Система контроля версий', 'База данных', 'Веб-сервер'],
        'correct': 1
    }
]

IQ_TEST_QUESTIONS = [
    {
        'question': 'Какое число следующее в последовательности: 2, 4, 8, 16, ?',
        'options': ['24', '32', '30', '28'],
        'correct': 1
    },
    {
        'question': 'Если A = 1, B = 2, C = 3, то CAB = ?',
        'options': ['312', '321', '123', '132'],
        'correct': 0
    },
    {
        'question': 'Найдите лишнее: Собака, Кошка, Лошадь, Стол',
        'options': ['Собака', 'Кошка', 'Лошадь', 'Стол'],
        'correct': 3
    },
    {
        'question': 'Какое слово не подходит к остальным: Красный, Синий, Высокий, Зеленый',
        'options': ['Красный', 'Синий', 'Высокий', 'Зеленый'],
        'correct': 2
    },
    {
        'question': 'Продолжите последовательность: 1, 1, 2, 3, 5, 8, ?',
        'options': ['11', '13', '15', '10'],
        'correct': 1
    },
    {
        'question': 'Сколько минут в 2.5 часах?',
        'options': ['120', '150', '180', '90'],
        'correct': 1
    },
    {
        'question': 'Если сегодня понедельник, какой день будет через 15 дней?',
        'options': ['Понедельник', 'Вторник', 'Среда', 'Четверг'],
        'correct': 1
    },
    {
        'question': 'Какое число получится: 25% от 80?',
        'options': ['15', '20', '25', '30'],
        'correct': 1
    },
    {
        'question': 'Антоним слова "высокий":',
        'options': ['Большой', 'Низкий', 'Широкий', 'Длинный'],
        'correct': 1
    },
    {
        'question': 'Решите: 7 × 8 - 6 × 9 = ?',
        'options': ['2', '1', '3', '0'],
        'correct': 0
    }
]

EQ_TEST_QUESTIONS = [
    {
        'question': 'Как вы обычно реагируете на критику?',
        'options': ['Принимаю к сведению и анализирую', 'Сразу защищаюсь', 'Игнорирую', 'Расстраиваюсь'],
        'correct': 0
    },
    {
        'question': 'Что вы делаете, когда видите расстроенного коллегу?',
        'options': ['Подхожу и предлагаю помощь', 'Делаю вид, что не замечаю', 'Жду, пока обратится сам', 'Сообщаю руководству'],
        'correct': 0
    },
    {
        'question': 'Как вы справляетесь со стрессом?',
        'options': ['Планирую и организую', 'Ищу поддержку у других', 'Избегаю стрессовых ситуаций', 'Переношу на других'],
        'correct': 0
    },
    {
        'question': 'При конфликте в команде вы:',
        'options': ['Ищете компромисс', 'Отстаиваете свою позицию', 'Уходите от конфликта', 'Привлекаете третью сторону'],
        'correct': 0
    },
    {
        'question': 'Как вы мотивируете себя на достижение целей?',
        'options': ['Ставлю четкие планы', 'Ищу вдохновение', 'Жду внешней мотивации', 'Работаю под давлением'],
        'correct': 0
    },
    {
        'question': 'Ваша реакция на неудачу:',
        'options': ['Анализирую ошибки и учусь', 'Расстраиваюсь надолго', 'Обвиняю обстоятельства', 'Сразу сдаюсь'],
        'correct': 0
    },
    {
        'question': 'Как вы воспринимаете эмоции других людей?',
        'options': ['Легко понимаю и сочувствую', 'Замечаю, но не всегда понимаю', 'Редко обращаю внимание', 'Считаю неважными'],
        'correct': 0
    },
    {
        'question': 'При работе в команде вы:',
        'options': ['Активно участвуете и поддерживаете', 'Работаете самостоятельно', 'Выполняете минимум', 'Руководите процессом'],
        'correct': 0
    },
    {
        'question': 'Ваш подход к решению проблем:',
        'options': ['Рассматриваю разные варианты', 'Действую интуитивно', 'Жду, пока решится само', 'Перекладываю на других'],
        'correct': 0
    },
    {
        'question': 'Как вы относитесь к изменениям?',
        'options': ['Принимаю и адаптируюсь', 'Настороженно, но приспосабливаюсь', 'Сопротивляюсь', 'Избегаю'],
        'correct': 0
    }
]

# Константы для комиссии
COMMISSION_EMAILS = [
    'commission1@university.com',
    'commission2@university.com', 
    'commission3@university.com',
    'commission4@university.com',
    'commission5@university.com'
]

def get_test_questions(test_type):
    """Получение вопросов для тестов по типу"""
    questions_map = {
        'iq': IQ_TEST_QUESTIONS,
        'eq': EQ_TEST_QUESTIONS,
        'custom': PROGRAMMING_TEST_QUESTIONS
    }
    return questions_map.get(test_type, [])

def create_user_if_not_exists(email, first_name, last_name, middle_name, role, password, department_id=None):
    """Создает пользователя если он не существует"""
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return existing_user
    
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        middle_name=middle_name,
        role=role,
        department_id=department_id
    )
    user.set_password(password)
    db.session.add(user)
    return user

def create_test_if_not_exists(name, test_type, created_by_id, questions=None):
    """Создает тест если он не существует"""
    existing_test = Test.query.filter_by(name=name).first()
    if existing_test:
        return existing_test
    
    if questions is None:
        questions = get_test_questions(test_type)
    
    test = Test(
        name=name,
        type=test_type,
        questions=json.dumps(questions, ensure_ascii=False),
        created_by=created_by_id,
        is_active=True
    )
    db.session.add(test)
    return test

def create_simple_test_data():
    """Создание простых тестовых данных для быстрого старта"""
    print("🚀 Создание простых тестовых данных...")
    
    with app.app_context():
        # Создание HR пользователя
        hr_user = User.query.filter_by(email='hr@example.com').first()
        if not hr_user:
            hr_user = User(
                email='hr@example.com',
                first_name='Анна',
                last_name='Петрова',
                role='hr'
            )
            hr_user.set_password('password123')
            db.session.add(hr_user)
            
        # Создание департамента
        dept = Department.query.filter_by(name='Факультет информационных технологий').first()
        if not dept:
            dept = Department(name='Факультет информационных технологий')
            db.session.add(dept)
            
        db.session.commit()
        
        # Создание тестов с использованием helper функции
        tests_to_create = [
            ('Тест по программированию', 'custom'),
            ('Стандартный IQ тест', 'iq'),
            ('Стандартный EQ тест', 'eq')
        ]
        
        created_tests = []
        for name, test_type in tests_to_create:
            test = create_test_if_not_exists(name, test_type, hr_user.id)
            created_tests.append(test)
        
        db.session.commit()
        
        print(f'✅ Создан HR пользователь: {hr_user.email}')
        print(f'✅ Создан департамент: {dept.name}')
        print(f'✅ Создано тестов: {len(created_tests)}')
        print()
        print('Данные для входа:')
        print('Email: hr@example.com')
        print('Пароль: password123')

def get_magic_links():
    """Получение всех magic links для тестирования"""
    print("🔗 Magic Links для тестирования голосования комиссии")
    print("=" * 60)
    
    with app.app_context():
        votes = CommissionVote.query.all()
        
        if not votes:
            print("⚠️  Нет голосований в базе данных.")
            print("Сначала создайте полные тестовые данные.")
            return
        
        print(f"Найдено голосований: {len(votes)}")
        print()
        
        # Группируем по заявкам
        by_application = {}
        for vote in votes:
            app_id = vote.application_id
            if app_id not in by_application:
                by_application[app_id] = []
            by_application[app_id].append(vote)
        
        for app_id, app_votes in by_application.items():
            application = Application.query.get(app_id)
            print(f"📋 Заявка #{app_id}: {application.candidate.full_name}")
            print(f"   Вакансия: {application.vacancy.title}")
            print(f"   Статус: {application.status}")
            print(f"   Голосований: {len(app_votes)}")
            print()
            
            for i, vote in enumerate(app_votes, 1):
                print(f"   👤 Член комиссии #{i}")
                print(f"      Email: {vote.voter_email}")
                print(f"      Link: http://127.0.0.1:5000/vote/{vote.magic_token}")
                print(f"      Использована: {'Да' if vote.token_used else 'Нет'}")
                if vote.vote:
                    print(f"      Голос: {vote.vote}")
                print()
            
            print("-" * 60)
        
        print("\n💡 Инструкции:")
        print("1. Скопируйте любую ссылку")
        print("2. Откройте в браузере")
        print("3. Заполните форму голосования")
        print("4. Проверьте результаты в HR панели")

def create_default_admin():
    """Создание администратора по умолчанию"""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = create_user_if_not_exists(
            'admin@university.com',
            'Администратор',
            'Системы',
            '',
            'admin',
            'admin123'
        )
        db.session.commit()
        print("✅ Администратор создан (admin@university.com / admin123)")
        return admin
    else:
        print("✅ Администратор уже существует")
        return admin

def create_test_departments():
    """Создание реальных департаментов АУЭС"""
    if not Department.query.first():
        departments = [Department(name=dept_name) for dept_name in AUES_DEPARTMENTS]
        db.session.add_all(departments)
        db.session.commit()
        print("✅ Реальные департаменты АУЭС созданы")
        return departments
    else:
        print("✅ Департаменты уже существуют")
        return Department.query.all()

def create_test_hr_users():
    """Создание HR пользователей АУЭС"""
    created_count = 0
    
    for hr_info in AUES_HR_USERS:
        existing_user = User.query.filter_by(email=hr_info['email']).first()
        if not existing_user:
            create_user_if_not_exists(
                hr_info['email'], 
                hr_info['first_name'], 
                hr_info['last_name'], 
                hr_info['middle_name'], 
                'hr', 
                'aues2024'
            )
            created_count += 1
    
    if created_count > 0:
        db.session.commit()
        print(f"✅ Созданы {created_count} HR пользователей АУЭС")
    else:
        print("✅ HR пользователи уже существуют")
    
    return User.query.filter_by(role='hr').all()

def create_test_department_heads():
    """Создание реальных глав департаментов АУЭС"""
    departments = Department.query.all()
    
    if not departments:
        print("⚠️  Сначала нужно создать департаменты")
        return []
    
    created_heads = []
    for head_data in AUES_DEPARTMENT_HEADS:
        if not User.query.filter_by(email=head_data['email']).first():
            # Находим департамент по названию
            dept = Department.query.filter_by(name=head_data['dept_name']).first()
            if not dept:
                print(f"⚠️  Департамент '{head_data['dept_name']}' не найден")
                continue
            
            dept_head = User(
                email=head_data['email'],
                first_name=head_data['first_name'],
                last_name=head_data['last_name'],
                middle_name=head_data['middle_name'],
                role='department_head',
                department_id=dept.id
            )
            dept_head.set_password('aues2024')
            created_heads.append(dept_head)
            
            db.session.add(dept_head)
            db.session.flush()  # Получаем ID пользователя
            
            # Назначаем главой департамента
            dept.head_id = dept_head.id
    
    if created_heads:
        db.session.commit()
        print(f"✅ Созданы {len(created_heads)} реальных глав департаментов АУЭС")
    else:
        print("✅ Главы департаментов уже существуют")
    
    return User.query.filter_by(role='department_head').all()

def create_test_candidates():
    """Создание тестовых кандидатов"""
    created_count = 0
    
    for candidate_data in CANDIDATES_DATA:
        existing_user = User.query.filter_by(email=candidate_data['email']).first()
        if not existing_user:
            create_user_if_not_exists(
                candidate_data['email'],
                candidate_data['first_name'],
                candidate_data['last_name'],
                candidate_data['middle_name'],
                'candidate',
                'candidate123'
            )
            created_count += 1
    
    if created_count > 0:
        db.session.commit()
        print("✅ Тестовые кандидаты созданы")
    else:
        print("✅ Кандидаты уже существуют")
    
    return User.query.filter_by(role='candidate').all()

def create_test_vacancies():
    """Создание реальных вакансий для АУЭС"""
    hr_users = User.query.filter_by(role='hr').all()
    departments = Department.query.all()
    
    if not hr_users:
        print("⚠️  Нет HR пользователей для создания вакансий")
        return []
    
    if not departments:
        print("⚠️  Нет департаментов для создания вакансий")
        return []
    
    # Создаем словарь департаментов для быстрого поиска
    dept_dict = {dept.name: dept.id for dept in departments}
    
    vacancies_data = [
        {
            'title': 'Преподаватель автоматизации и управления',
            'department_name': 'Кафедра автоматизации и управления (АУ)',
            'discipline': 'Теория автоматического управления',
            'employment_type': 'full',
            'work_format': 'hybrid',
            'education_level': 'master',
            'required_specialty': 'Автоматизация и управление техническими системами',
            'min_experience': 3,
            'description': 'Требуется преподаватель для ведения дисциплин по автоматизации и управлению техническими системами.\n\nОбязанности:\n- Проведение лекций и практических занятий\n- Разработка лабораторных работ\n- Научная работа в области автоматизации\n- Руководство дипломными проектами\n\nТребования:\n- Высшее техническое образование\n- Опыт работы с системами автоматизации\n- Знание MATLAB, Simulink\n- Публикации в технических журналах приветствуются',
            'salary': '200,000 - 280,000 тенге',
            'required_test_types': ['iq', 'custom']
        },
        {
            'title': 'Доцент кафедры IT-инженерии',
            'department_name': 'Кафедра IT-инженерии и искусственного интеллекта (ITЕ)',
            'discipline': 'Искусственный интеллект и машинное обучение',
            'employment_type': 'full',
            'work_format': 'hybrid',
            'education_level': 'phd',
            'required_specialty': 'Информационные технологии, Компьютерная инженерия',
            'min_experience': 5,
            'description': 'Ищем доцента для преподавания дисциплин по искусственному интеллекту и машинному обучению.\n\nОбязанности:\n- Ведение курсов по ИИ и ML\n- Разработка учебных программ\n- Научно-исследовательская деятельность\n- Подготовка публикаций\n\nТребования:\n- PhD в области IT или смежных наук\n- Опыт работы с Python, TensorFlow, PyTorch\n- Международные публикации\n- Знание английского языка',
            'salary': '250,000 - 350,000 тенге',
            'required_test_types': ['iq', 'eq']
        },
        {
            'title': 'Преподаватель кибербезопасности',
            'department_name': 'Кафедра кибербезопасности (КБ)',
            'discipline': 'Защита информационных систем',
            'employment_type': 'full',
            'work_format': 'office',
            'education_level': 'master',
            'required_specialty': 'Информационная безопасность, Кибербезопасность',
            'min_experience': 2,
            'description': 'Требуется специалист для преподавания дисциплин по кибербезопасности.\n\nОбязанности:\n- Проведение занятий по защите информации\n- Практические работы в лабораториях\n- Подготовка студентов к сертификациям\n- Участие в проектах по ИБ\n\nТребования:\n- Образование в области ИБ\n- Знание сетевых технологий\n- Опыт работы с системами защиты\n- Сертификации CISSP, CEH приветствуются',
            'salary': '220,000 - 300,000 тенге',
            'required_test_types': ['iq', 'custom']
        },
        {
            'title': 'Профессор теплоэнергетики',
            'department_name': 'Кафедра теплоэнергетики и физики (ТЭ и Ф)',
            'discipline': 'Теплотехника и теплоэнергетика',
            'employment_type': 'full',
            'work_format': 'office',
            'education_level': 'phd',
            'required_specialty': 'Теплоэнергетика, Теплотехника',
            'min_experience': 10,
            'description': 'Приглашаем ведущего специалиста на должность профессора кафедры теплоэнергетики.\n\nОбязанности:\n- Ведение профильных дисциплин\n- Руководство научными исследованиями\n- Подготовка докторантов\n- Участие в грантовых проектах\n\nТребования:\n- Докторская степень в области теплоэнергетики\n- Международный опыт\n- Высокий индекс цитирования\n- Руководство крупными проектами',
            'salary': '400,000 - 600,000 тенге',
            'required_test_types': ['iq', 'eq', 'custom']
        },
        {
            'title': 'Ассистент кафедры электроэнергетики',
            'department_name': 'Кафедра электроэнергетики (ЭЭ)',
            'discipline': 'Электрические станции и подстанции',
            'employment_type': 'part',
            'work_format': 'hybrid',
            'education_level': 'bachelor',
            'required_specialty': 'Электроэнергетика',
            'min_experience': 0,
            'description': 'Приглашаем молодого специалиста для работы ассистентом на кафедре электроэнергетики.\n\nОбязанности:\n- Проведение практических занятий\n- Помощь в лабораторных работах\n- Подготовка учебных материалов\n- Участие в научной работе кафедры\n\nТребования:\n- Высшее образование по электроэнергетике\n- Знание основ электротехники\n- Желание развиваться в науке\n- Коммуникативные навыки',
            'salary': '140,000 - 200,000 тенге',
            'required_test_types': ['iq']
        },
        {
            'title': 'Преподаватель математики',
            'department_name': 'Кафедра математики',
            'discipline': 'Высшая математика',
            'employment_type': 'full',
            'work_format': 'office',
            'education_level': 'master',
            'required_specialty': 'Математика, Прикладная математика',
            'min_experience': 2,
            'description': 'Требуется преподаватель математики для технических специальностей.\n\nОбязанности:\n- Ведение курсов высшей математики\n- Проведение практических занятий\n- Консультации студентов\n- Подготовка методических материалов\n\nТребования:\n- Математическое образование\n- Опыт преподавания в техническом вузе\n- Знание прикладных аспектов математики\n- Терпение и педагогические навыки',
            'salary': '180,000 - 250,000 тенге',
            'required_test_types': ['iq', 'eq']
        },
        {
            'title': 'Преподаватель английского языка',
            'department_name': 'Кафедра языков',
            'discipline': 'Английский язык для технических специальностей',
            'employment_type': 'full',
            'work_format': 'hybrid',
            'education_level': 'master',
            'required_specialty': 'Лингвистика, Филология',
            'min_experience': 2,
            'description': 'Ищем преподавателя английского языка для студентов технических специальностей.\n\nОбязанности:\n- Преподавание технического английского\n- Развитие языковых навыков студентов\n- Подготовка к международным экзаменам\n- Разработка специализированных курсов\n\nТребования:\n- Высшее филологическое образование\n- Уровень английского C1/C2\n- Опыт преподавания ESP\n- Международные сертификаты приветствуются',
            'salary': '170,000 - 230,000 тенге',
            'required_test_types': ['eq']
        }
    ]
    
    created_vacancies = []
    for i, vacancy_data in enumerate(vacancies_data):
        hr_user = hr_users[i % len(hr_users)]  # Распределяем между HR
        
        # Находим ID департамента по названию
        dept_id = dept_dict.get(vacancy_data['department_name'])
        if not dept_id:
            print(f"⚠️  Департамент '{vacancy_data['department_name']}' не найден")
            continue
        
        if not Vacancy.query.filter_by(title=vacancy_data['title']).first():
            vacancy = Vacancy(
                title=vacancy_data['title'],
                department_id=dept_id,
                discipline=vacancy_data['discipline'],
                employment_type=vacancy_data['employment_type'],
                work_format=vacancy_data['work_format'],
                education_level=vacancy_data['education_level'],
                required_specialty=vacancy_data['required_specialty'],
                min_experience=vacancy_data['min_experience'],
                application_start=datetime.utcnow(),
                application_end=datetime.utcnow() + timedelta(days=30),
                work_start_date=datetime.utcnow() + timedelta(days=60),
                created_by=hr_user.id,
                contact_person=hr_user.full_name,
                contact_email=hr_user.email,
                description=vacancy_data['description'],
                salary=vacancy_data['salary']
            )
            
            db.session.add(vacancy)
            db.session.flush()  # Получаем ID вакансии
            
            # Добавляем требуемые тесты по типам
            for test_type in vacancy_data['required_test_types']:
                # Ищем тесты по типу
                tests = Test.query.filter_by(type=test_type, is_active=True).all()
                for test in tests:
                    if test not in vacancy.required_tests:
                        vacancy.required_tests.append(test)
            
            created_vacancies.append(vacancy)
    
    if created_vacancies:
        db.session.commit()
        print(f"✅ Созданы {len(created_vacancies)} реальных вакансий АУЭС")
    else:
        print("✅ Вакансии уже существуют")
    
    return Vacancy.query.all()

def create_test_tests():
    """Создание тестовых тестов IQ/EQ"""
    hr_users = User.query.filter_by(role='hr').all()
    if not hr_users:
        print("⚠️  Нет HR пользователей для создания тестов")
        return []
    
    tests_data = [
        ('Стандартный IQ тест для ППС', 'iq'),
        ('Тест эмоционального интеллекта для преподавателей', 'eq'),
        ('Расширенный IQ тест для IT-специалистов', 'iq'),
        ('EQ тест для работы в команде', 'eq'),
        ('Тест по основам программирования', 'custom')
    ]
    
    created_tests = []
    for i, (name, test_type) in enumerate(tests_data):
        hr_user = hr_users[i % len(hr_users)]
        test = create_test_if_not_exists(name, test_type, hr_user.id)
        created_tests.append(test)
    
    if created_tests:
        db.session.commit()
        print("✅ Тестовые тесты созданы")
    else:
        print("✅ Тесты уже существуют")
    
    return Test.query.all()

def create_test_applications():
    """Создание тестовых заявок от кандидатов"""
    candidates = User.query.filter_by(role='candidate').all()
    vacancies = Vacancy.query.all()
    
    if not candidates or not vacancies:
        print("⚠️  Нет кандидатов или вакансий для создания заявок")
        return []
    
    applications_data = [
        {
            'candidate_email': 'candidate1@example.com',
            'vacancy_title': 'Доцент кафедры IT-инженерии',
            'birth_date': datetime(1990, 5, 15).date(),
            'citizenship': 'Республика Казахстан',
            'city': 'Алматы',
            'phone': '+7 777 123 4567',
            'marital_status': 'Женат/Замужем',
            'military_status': 'Служил, освобожден',
            'no_criminal_record': True,
            'has_disability': False,
            'is_pensioner': False,
            'work_experience': 'ТОО "Kaspi Bank", Ведущий разработчик (2014-2020)\nТОО "Halyk Bank", Архитектор ПО (2020-2023)\nКазНУ им. аль-Фараби, Преподаватель (совместительство, 2021-н.в.)',
            'academic_degree': 'PhD',
            'academic_title': 'Ассоциированный профессор',
            'title_date': datetime(2021, 6, 15).date(),
            'publications_count': 15,
            'key_publications': '1. "Методы машинного обучения в финтех" - Вестник КазНУ, 2022\n2. "Архитектура микросервисов в банковских системах" - International Journal of Computer Science, 2021\n3. "Применение блокчейна в образовании" - Материалы конференции AITU, 2023',
            'projects_count': 8,
            'projects_list': '1. Система дистанционного обучения для КазНУ (руководитель)\n2. Мобильное приложение для банка (технический лидер)\n3. Исследование ИИ в образовании (грант МОН РК)',
            'h_index': 5,
            'patents': '2 патента на изобретения в области ИТ',
            'courses': 'Курсы AWS (2020), Machine Learning Coursera (2021), Педагогические технологии (КазНУ, 2022)',
            'languages': 'Казахский (родной), Русский (свободно), Английский (продвинутый), Китайский (базовый)',
            'awards': 'Лучший преподаватель года КазНУ (2022), Грант "Лучший молодой ученый" (2021)',
            'video_presentation': 'https://youtube.com/watch?v=example1',
            'data_processing_consent': True,
            'video_audio_consent': True
        },
        {
            'candidate_email': 'candidate2@example.com',
            'vacancy_title': 'Преподаватель кибербезопасности',
            'birth_date': datetime(1985, 12, 8).date(),
            'citizenship': 'Республика Казахстан',
            'city': 'Алматы',
            'phone': '+7 777 234 5678',
            'marital_status': 'Холост/Не замужем',
            'military_status': 'Не подлежит призыву',
            'no_criminal_record': True,
            'has_disability': False,
            'is_pensioner': False,
            'work_experience': 'ТОО "Цифровые технологии", Специалист по ИБ (2010-2015)\nТОО "SecureNet", Ведущий специалист по кибербезопасности (2015-2020)\nФриланс консультант по ИБ (2020-н.в.)',
            'academic_degree': 'Кандидат технических наук',
            'academic_title': 'Доцент',
            'title_date': datetime(2020, 3, 10).date(),
            'publications_count': 12,
            'key_publications': '1. "Современные методы защиты от кибератак" - Журнал КИБ, 2021\n2. "Анализ уязвимостей веб-приложений" - Безопасность информационных технологий, 2022\n3. "Машинное обучение в кибербезопасности" - Материалы конференции InfoSec, 2023',
            'projects_count': 6,
            'projects_list': '1. Система мониторинга сетевой безопасности для банка\n2. Разработка политик ИБ для госучреждений\n3. Исследование IoT безопасности (грант КН МОН РК)',
            'h_index': 3,
            'patents': '1 патент на систему обнаружения вторжений',
            'courses': 'CISSP (2018), CEH (2019), Курсы по этичному хакингу (2020)',
            'languages': 'Казахский (родной), Русский (свободно), Английский (продвинутый)',
            'awards': 'Лучший специалист по ИБ года (2019), Грант молодого ученого (2020)',
            'video_presentation': 'https://youtube.com/watch?v=example2',
            'data_processing_consent': True,
            'video_audio_consent': True
        },
        {
            'candidate_email': 'candidate3@example.com',
            'vacancy_title': 'Преподаватель математики',
            'birth_date': datetime(1988, 7, 22).date(),
            'citizenship': 'Республика Казахстан',
            'city': 'Нур-Султан',
            'phone': '+7 777 345 6789',
            'marital_status': 'Женат/Замужем',
            'military_status': 'Служил',
            'no_criminal_record': True,
            'has_disability': False,
            'is_pensioner': False,
            'work_experience': 'КазНУ им. аль-Фараби, Преподаватель математики (2012-2018)\nНазарбаев Университет, Старший преподаватель (2018-2023)\nОнлайн школа MathPro, Методист (совместительство, 2020-н.в.)',
            'academic_degree': 'Кандидат физико-математических наук',
            'academic_title': 'Доцент',
            'title_date': datetime(2019, 9, 5).date(),
            'publications_count': 18,
            'key_publications': '1. "Применение высшей математики в инженерных расчетах" - Вестник КазНУ, 2021\n2. "Дифференциальные уравнения в технических системах" - Математический вестник, 2022\n3. "Численные методы решения инженерных задач" - Прикладная математика, 2023',
            'projects_count': 4,
            'projects_list': '1. Разработка методики преподавания математики для инженеров\n2. Электронный учебник по высшей математике\n3. Система автоматической проверки математических заданий',
            'h_index': 4,
            'patents': 'Нет',
            'courses': 'Современные методы преподавания математики (2020), Цифровые технологии в образовании (2021)',
            'languages': 'Казахский (родной), Русский (свободно), Английский (хороший)',
            'awards': 'Лучший преподаватель НУ (2021), Благодарность МОН РК (2022)',
            'video_presentation': '',
            'data_processing_consent': True,
            'video_audio_consent': True
        }
    ]
    
    created_applications = []
    for app_data in applications_data:
        candidate = User.query.filter_by(email=app_data['candidate_email']).first()
        vacancy = Vacancy.query.filter_by(title=app_data['vacancy_title']).first()
        
        if candidate and vacancy:
            if not Application.query.filter_by(candidate_id=candidate.id, vacancy_id=vacancy.id).first():
                application = Application(
                    vacancy_id=vacancy.id,
                    candidate_id=candidate.id,
                    birth_date=app_data.get('birth_date'),
                    citizenship=app_data.get('citizenship'),
                    city=app_data.get('city'),
                    phone=app_data.get('phone'),
                    marital_status=app_data.get('marital_status'),
                    military_status=app_data.get('military_status'),
                    no_criminal_record=app_data.get('no_criminal_record', False),
                    has_disability=app_data.get('has_disability', False),
                    is_pensioner=app_data.get('is_pensioner', False),
                    work_experience=app_data.get('work_experience'),
                    academic_degree=app_data.get('academic_degree'),
                    academic_title=app_data.get('academic_title'),
                    title_date=app_data.get('title_date'),
                    publications_count=app_data.get('publications_count', 0),
                    key_publications=app_data.get('key_publications'),
                    projects_count=app_data.get('projects_count', 0),
                    projects_list=app_data.get('projects_list'),
                    h_index=app_data.get('h_index'),
                    patents=app_data.get('patents'),
                    courses=app_data.get('courses'),
                    languages=app_data.get('languages'),
                    awards=app_data.get('awards'),
                    video_presentation=app_data.get('video_presentation'),
                    data_processing_consent=app_data.get('data_processing_consent', False),
                    video_audio_consent=app_data.get('video_audio_consent', False),
                    status='hr_review',  # Заявки готовы к рассмотрению
                    # Инициализируем поля для доработки
                    revision_requested=False,
                    revision_count=0
                )
                created_applications.append(application)
    
    if created_applications:
        db.session.add_all(created_applications)
        db.session.commit()
        
        # Создаем одну заявку с доработкой для демонстрации
        if len(created_applications) > 0:
            revision_application = created_applications[0]
            revision_application.status = 'revision_requested'
            revision_application.revision_requested = True
            revision_application.revision_notes = 'Пожалуйста, дополните информацию о ваших публикациях более подробным описанием вклада в каждую работу. Также требуется указать соавторов и импакт-фактор журналов.'
            revision_application.revision_requested_date = datetime.utcnow()
            revision_application.revision_count = 1
            revision_application.hr_decision = 'request_revision'
            revision_application.hr_decision_date = datetime.utcnow()
            db.session.commit()
            print("✅ Создана заявка с доработкой для демонстрации")
        
        print("✅ Тестовые заявки созданы")
    else:
        print("✅ Заявки уже существуют")
    
    return Application.query.all()

def create_test_results():
    """Создание результатов тестов для заявок"""
    applications = Application.query.all()
    
    if not applications:
        print("⚠️  Нет заявок для создания результатов")
        return []
    
    created_results = []
    for application in applications:
        # Получаем требуемые тесты для вакансии
        required_tests = application.vacancy.required_tests
        
        for test in required_tests:
            # Проверяем, нет ли уже результата для этого теста
            existing_result = TestResult.query.filter_by(
                    application_id=application.id,
                test_id=test.id
            ).first()
        
            if not existing_result:
                # Генерируем случайный результат
                questions = json.loads(test.questions)
                score = random.randint(6, len(questions))  # От 60% до 100%
                
                # Генерируем случайные ответы
                answers = [random.randint(0, 3) for _ in range(len(questions))]
                
                test_result = TestResult(
                    application_id=application.id,
                    test_id=test.id,
                    test_type=test.type,
                    answers=json.dumps(answers),
                    score=score,
                    max_score=len(questions)
                )
                created_results.append(test_result)
    
    if created_results:
        db.session.add_all(created_results)
        db.session.commit()
        print("✅ Результаты тестов созданы")
    else:
        print("✅ Результаты тестов уже существуют")
    
    return TestResult.query.all()

def create_test_commission_votes():
    """Создание тестовых голосований комиссии"""
    # Находим заявки со статусом hr_review для создания голосований
    applications = Application.query.filter_by(status='hr_review').all()
    
    if not applications:
        print("⚠️  Нет заявок для создания голосований комиссии")
        return []
    
    created_votes = []
    
    # Для первой заявки создаем полный набор голосований
    if applications:
        first_app = applications[0]
        first_app.status = 'interview_scheduled'
        first_app.interview_date = datetime.utcnow() + timedelta(days=7)
        first_app.interview_format = 'online'
        first_app.interview_link = 'https://zoom.us/j/123456789'
        
        for email in COMMISSION_EMAILS:
            if not CommissionVote.query.filter_by(application_id=first_app.id, voter_email=email).first():
                vote = CommissionVote(
                    application_id=first_app.id,
                    voter_email=email
                )
                created_votes.append(vote)
    
    if created_votes:
        db.session.add_all(created_votes)
        db.session.commit()
        print("✅ Тестовые голосования комиссии созданы")
    else:
        print("✅ Голосования комиссии уже существуют")
    
    return CommissionVote.query.all()

def init_project():
    """Инициализация проекта с полными тестовыми данными"""
    print("🎓 Инициализация HR платформы поиска ППС")
    print("=" * 50)
    
    with app.app_context():
        # Создаем таблицы
        db.create_all()
        print("✅ База данных создана")
        
        # Создаем всех пользователей и данные
        admin = create_default_admin()
        departments = create_test_departments()
        hr_users = create_test_hr_users()
        dept_heads = create_test_department_heads()
        candidates = create_test_candidates()
        tests = create_test_tests()
        vacancies = create_test_vacancies()
        applications = create_test_applications()
        results = create_test_results()
        votes = create_test_commission_votes()
        
        print("\n" + "=" * 50)
        print("🎉 Проект успешно инициализирован!")
        print("\n📋 Созданные тестовые аккаунты:")
        print("👑 Администратор: admin@university.com / admin123")
        print("👤 HR специалисты:")
        for hr in hr_users:
            print(f"   📧 {hr.email} / aues2024")
        print("👤 Главы департаментов:")
        for head in dept_heads:
            print(f"   📧 {head.email} / aues2024")
        print("👤 Кандидаты:")
        for candidate in candidates:
            print(f"   📧 {candidate.email} / candidate123")
        
        print(f"\n📊 Статистика:")
        print(f"   Департаментов: {len(departments)}")
        print(f"   Вакансий: {len(vacancies)}")
        print(f"   Пользователей: {User.query.count()}")
        print(f"   Тестов: {Test.query.count()}")
        print(f"   Заявок: {Application.query.count()}")
        print(f"   Результатов тестов: {TestResult.query.count()}")
        print(f"   Голосований комиссии: {CommissionVote.query.count()}")
        
        print("\n🚀 Для запуска приложения используйте: python run.py")
        print("🌐 Откройте браузер: http://localhost:5000")
        print("=" * 50)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'simple':
            print("Создание простых тестовых данных...")
            create_simple_test_data()
        elif command == 'links':
            get_magic_links()
        elif command == 'full':
            init_project()
        else:
            print("Доступные команды:")
            print("  simple - создание простых тестовых данных")
            print("  links  - показать magic links для голосования")
            print("  full   - полная инициализация проекта")
    else:
        init_project()