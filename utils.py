import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import request, current_app
from models import AuditLog, db
from email_config import get_email_config

# Константы для статусов заявок
APPLICATION_STATUSES = {
    'pending': 'Ожидает обработки',
    'hr_review': 'На рассмотрении HR',
    'revision_requested': 'Требуется доработка',
    'dept_review': 'На рассмотрении у главы департамента',
    'interview_scheduled': 'Назначено интервью',
    'voting': 'Голосование комиссии',
    'approved': 'Одобрено',
    'rejected': 'Отклонено'
}

# Константы для ролей пользователей
USER_ROLES = {
    'admin': 'Администратор',
    'hr': 'HR специалист',
    'department_head': 'Глава департамента',
    'candidate': 'Кандидат'
}

# Константы для уровня образования
EDUCATION_LEVELS = {
    'bachelor': 'Бакалавр',
    'master': 'Магистр',
    'phd': 'PhD/Кандидат наук'
}

# Константы для типов занятости
EMPLOYMENT_TYPES = {
    'full': 'Полная занятость',
    'part': 'Частичная занятость',
    'guest': 'Гостевая'
}

# Константы для формата работы
WORK_FORMATS = {
    'office': 'Очно',
    'online': 'Онлайн',
    'hybrid': 'Гибрид'
}

def send_email(to_email, subject, html_content, smtp_config=None):
    """Отправка email уведомлений"""
    # Получаем конфигурацию
    config = get_email_config()
    
    # В тестовом режиме просто логируем
    if config['TESTING_MODE']:
        print(f"""
=== ТЕСТОВЫЙ РЕЖИМ EMAIL ===
Кому: {to_email}
Тема: {subject}
Содержимое: {html_content[:200]}...
=============================
        """)
        return True
    
    try:
        if not smtp_config:
            smtp_config = {
                'server': config['SMTP_SERVER'],
                'port': config['SMTP_PORT'],
                'username': config['SMTP_USERNAME'],
                'password': config['SMTP_PASSWORD'],
                'use_tls': config['SMTP_USE_TLS'],
                'from_name': config['FROM_NAME'],
                'from_email': config['FROM_EMAIL']
            }
        
        # Проверяем наличие обязательных настроек
        if not smtp_config['username'] or not smtp_config['password']:
            print("Ошибка: Не настроены SMTP_USERNAME или SMTP_PASSWORD")
            return False
        
        msg = MIMEMultipart('alternative')
        
        # Используем from_name если указан
        if smtp_config.get('from_name'):
            from_address = f"{Header(smtp_config['from_name'], 'utf-8').encode()} <{smtp_config.get('from_email', smtp_config['username'])}>"
        else:
            from_address = smtp_config.get('from_email', smtp_config['username'])
            
        msg['From'] = from_address
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8').encode()
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        print(f"Подключение к SMTP серверу: {smtp_config['server']}:{smtp_config['port']}")
        server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
        server.set_debuglevel(1)  # Включаем отладку
        
        if smtp_config['use_tls']:
            server.starttls()
        
        server.login(smtp_config['username'], smtp_config['password'])
        server.send_message(msg)
        server.quit()
        
        print(f"Email успешно отправлен на {to_email}")
        return True
        
    except Exception as e:
        print(f"Ошибка отправки email на {to_email}: {e}")
        return False

def send_revision_notification(application):
    """Отправка уведомления кандидату о необходимости доработки заявки"""
    config = get_email_config()
    subject = f"Требуется доработка заявки - {application.vacancy.title}"
    
    # HTML шаблон уведомления
    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <meta charset="utf-8">
            <title>Требуется доработка заявки</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #ffc107; color: #212529; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f8f9fa; }}
                .revision-info {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; border-left: 4px solid #ffc107; }}
                .edit-button {{ 
                    display: inline-block; 
                    padding: 12px 25px; 
                    background-color: #007bff; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px; 
                    margin: 20px 0;
                }}
                .footer {{ background-color: #6c757d; color: white; padding: 15px; text-align: center; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>✏️ Требуется доработка заявки</h2>
                    <p>HR Платформа АУЭС</p>
                </div>
                
                <div class="content">
                    <p>Уважаемый(ая) {application.candidate.full_name}!</p>
                    <p>Ваша заявка на должность <strong>"{application.vacancy.title}"</strong> требует доработки.</p>
                    
                    <div class="revision-info">
                        <h3>📝 Комментарии HR специалиста:</h3>
                        <p style="margin: 0; white-space: pre-line;">{application.revision_notes}</p>
                    </div>
                    
                    <div class="revision-info">
                        <h3>📋 Информация о заявке:</h3>
                        <ul>
                            <li><strong>Вакансия:</strong> {application.vacancy.title}</li>
                            <li><strong>Дисциплина:</strong> {application.vacancy.discipline}</li>
                            <li><strong>Департамент:</strong> {application.vacancy.department.name}</li>
                            <li><strong>Номер доработки:</strong> #{application.revision_count}</li>
                            <li><strong>Дата запроса:</strong> {application.revision_requested_date.strftime('%d.%m.%Y в %H:%M')}</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{request.url_root}candidate/application/{application.id}/edit" class="edit-button">
                            ✏️ Перейти к редактированию заявки
                        </a>
                    </div>
                    
                    <div style="background-color: #d1ecf1; padding: 15px; border-radius: 5px; border-left: 4px solid #bee5eb;">
                        <strong>ℹ️ Что делать дальше:</strong>
                        <ul>
                            <li>Внимательно изучите комментарии HR специалиста</li>
                            <li>Внесите необходимые изменения в заявку</li>
                            <li>После сохранения изменений заявка автоматически вернется на рассмотрение</li>
                            <li>Вы можете отслеживать статус в личном кабинете</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Это автоматическое уведомление от HR платформы АУЭС</p>
                    <p>При возникновении вопросов обращайтесь в отдел кадров</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    try:
        success = send_email(application.candidate.email, subject, html_content)
        if success:
            print(f"✅ Уведомление о доработке отправлено: {application.candidate.email}")
        else:
            print(f"❌ Не удалось отправить уведомление: {application.candidate.email}")
        return success
    except Exception as e:
        print(f"❌ Ошибка при отправке уведомления о доработке: {e}")
        return False

def send_interview_invitation(application, commission_emails):
    """Отправка приглашений на интервью членам комиссии"""
    config = get_email_config()
    subject = f"Приглашение на интервью - {application.vacancy.title}"
    
    success_count = 0
    failed_emails = []
    
    for email in commission_emails:
        try:
            # Создаем запись голосования с магической ссылкой
            from models import CommissionVote
            vote = CommissionVote(
                application_id=application.id,
                voter_email=email.strip()
            )
            db.session.add(vote)
            db.session.commit()
            
            # Формируем ссылку для голосования
            vote_url = f"{request.url_root}vote/{vote.magic_token}"
            
            # Улучшенный HTML шаблон
            html_content = f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <meta charset="utf-8">
                    <title>Приглашение на интервью</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                        .content {{ padding: 20px; background-color: #f8f9fa; }}
                        .candidate-info {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                        .vote-button {{ 
                            display: inline-block; 
                            padding: 12px 25px; 
                            background-color: #28a745; 
                            color: white; 
                            text-decoration: none; 
                            border-radius: 5px; 
                            margin: 20px 0;
                        }}
                        .footer {{ background-color: #6c757d; color: white; padding: 15px; text-align: center; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h2>🎯 Приглашение на интервью</h2>
                            <p>Экспертная оценка кандидата</p>
                        </div>
                        
                        <div class="content">
                            <p>Уважаемый эксперт!</p>
                            <p>Вы приглашены принять участие в оценке кандидата на должность в АУЭС.</p>
                            
                            <div class="candidate-info">
                                <h3>📋 Информация о вакансии</h3>
                                <ul>
                                    <li><strong>Кандидат:</strong> {application.candidate.full_name}</li>
                                    <li><strong>Должность:</strong> {application.vacancy.title}</li>
                                    <li><strong>Дисциплина:</strong> {application.vacancy.discipline}</li>
                                    <li><strong>Департамент:</strong> {application.vacancy.department.name}</li>
                                    <li><strong>Дата интервью:</strong> {application.interview_date.strftime('%d.%m.%Y в %H:%M') if application.interview_date else 'Будет назначена дополнительно'}</li>
                                    {'<li><strong>Формат:</strong> ' + ('Онлайн' if application.interview_format == 'online' else 'Очно') + '</li>' if application.interview_format else ''}
                                    {'<li><strong>Ссылка:</strong> <a href="' + application.interview_link + '">' + application.interview_link + '</a></li>' if application.interview_link else ''}
                                    {'<li><strong>Адрес:</strong> ' + application.interview_address + '</li>' if application.interview_address else ''}
                                </ul>
                            </div>
                            
                            <div class="candidate-info">
                                <h3>👤 Краткая информация о кандидате</h3>
                                <p><strong>Образование:</strong> {(application.education or 'Не указано')[:200]}{'...' if application.education and len(application.education) > 200 else ''}</p>
                                <p><strong>Научная степень:</strong> {application.academic_degree or 'Не указана'}</p>
                                <p><strong>Публикации:</strong> {application.publications_count or 0}</p>
                                <p><strong>Научные проекты:</strong> {application.projects_count or 0}</p>
                                {f'<p><strong>Индекс Хирша:</strong> {application.h_index}</p>' if application.h_index else ''}
                            </div>
                
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{vote_url}" class="vote-button">
                                    🗳️ Перейти к голосованию
                                </a>
                            </div>
                            
                            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                                <strong>⚠️ Важно:</strong>
                                <ul>
                                    <li>Ссылка для голосования одноразовая</li>
                                    <li>После голосования ссылка станет недоступной</li>
                                    <li>Пожалуйста, внимательно ознакомьтесь с материалами перед принятием решения</li>
                                </ul>
                            </div>
                        </div>
                        
                        <div class="footer">
                            <p>Это автоматическое уведомление от HR платформы АУЭС</p>
                            <p>При возникновении вопросов обращайтесь в отдел кадров</p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            if send_email(email.strip(), subject, html_content):
                success_count += 1
                print(f"✅ Приглашение отправлено: {email}")
            else:
                failed_emails.append(email)
                print(f"❌ Не удалось отправить: {email}")
                
        except Exception as e:
            failed_emails.append(email)
            print(f"❌ Ошибка при отправке на {email}: {e}")
    
    # Логируем результат
    if config['TESTING_MODE']:
        print(f"""
=== РЕЗУЛЬТАТ ОТПРАВКИ ПРИГЛАШЕНИЙ ===
Успешно: {success_count}/{len(commission_emails)}
Тестовый режим: включен
======================================
        """)
    else:
        print(f"Отправлено приглашений: {success_count}/{len(commission_emails)}")
        if failed_emails:
            print(f"Не удалось отправить: {', '.join(failed_emails)}")
    
    return success_count > 0

def allowed_file(filename, allowed_extensions={'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}):
    """Проверка допустимых расширений файлов"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def allowed_pdf_file(filename):
    """Проверка что файл является PDF"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'pdf'

def save_uploaded_file(file, folder='uploads'):
    """Сохранение загруженного файла"""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Добавляем timestamp для уникальности
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        upload_folder = os.path.join(current_app.root_path, folder)
        os.makedirs(upload_folder, exist_ok=True)
        
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        return filename
    return None

def save_pdf_files(files, folder='uploads/documents'):
    """Сохранение множественных PDF файлов"""
    saved_files = []
    
    if not files:
        return saved_files
    
    # Если это один файл, превращаем в список
    if not isinstance(files, list):
        files = [files]
    
    for file in files:
        if file and file.filename and allowed_pdf_file(file.filename):
            filename = secure_filename(file.filename)
            # Добавляем timestamp для уникальности
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
            filename = timestamp + filename
            
            upload_folder = os.path.join(current_app.root_path, folder)
            os.makedirs(upload_folder, exist_ok=True)
            
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            saved_files.append(filename)
    
    return saved_files

def log_action(user_id, action, entity_type, entity_id=None, details=None):
    """Логирование действий пользователей"""
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=request.remote_addr if request else None
    )
    db.session.add(log_entry)
    db.session.commit()

def calculate_test_score(answers, correct_answers):
    """Подсчет результатов теста"""
    if not answers or not correct_answers:
        return 0
    
    score = 0
    for i, answer in enumerate(answers):
        if i < len(correct_answers) and answer == correct_answers[i]:
            score += 1
    
    return score

def get_test_questions(test_type='iq'):
    """Получение вопросов для тестов IQ/EQ"""
    if test_type == 'iq':
        return [
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
    elif test_type == 'eq':
        return [
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
    
    return []

def format_json_field(json_string, default=None):
    """Безопасное преобразование JSON строки в объект"""
    if not json_string:
        return default or {}
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return default or {}

def get_file_list_from_json(json_string):
    """Безопасное получение списка файлов из JSON строки"""
    if not json_string:
        return []
    try:
        result = json.loads(json_string)
        # Если результат это список, возвращаем его
        if isinstance(result, list):
            return result
        # Если это словарь, возвращаем пустой список
        elif isinstance(result, dict):
            return []
        # В остальных случаях тоже пустой список
        else:
            return []
    except (json.JSONDecodeError, TypeError):
        return []

def format_date(date_obj, format_str='%d.%m.%Y'):
    """Форматирование даты"""
    if not date_obj:
        return ''
    return date_obj.strftime(format_str)

def format_datetime(datetime_obj, format_str='%d.%m.%Y %H:%M'):
    """Форматирование даты и времени"""
    if not datetime_obj:
        return ''
    return datetime_obj.strftime(format_str)

def moment():
    """Получение текущего времени для шаблонов"""
    return datetime.utcnow()

def calculate_age(birth_date):
    """Вычисление возраста по дате рождения"""
    if not birth_date:
        return None
    today = datetime.utcnow().date()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def get_status_badge_class(status):
    """Получение CSS класса для бейджа статуса"""
    status_classes = {
        'pending': 'bg-secondary text-white',
        'hr_review': 'bg-info text-white',
        'revision_requested': 'bg-warning text-dark',
        'dept_review': 'bg-warning text-dark',
        'interview_scheduled': 'bg-primary text-white',
        'voting': 'bg-info text-white',
        'approved': 'bg-success text-white',
        'rejected': 'bg-danger text-white'
    }
    return status_classes.get(status, 'bg-secondary text-white')

def export_applications_to_excel(applications):
    """Экспорт заявок в Excel"""
    try:
        import pandas as pd
        from models import TestResult
        
        data = []
        for app in applications:
            # Получаем результаты тестов из новой системы
            test_results = TestResult.query.filter_by(application_id=app.id).all()
            
            # Формируем строку с результатами тестов
            test_results_str = ""
            if test_results:
                results_list = []
                for result in test_results:
                    test_name = result.test.name if result.test else f"Тест ID {result.test_id}"
                    results_list.append(f"{test_name}: {result.score}/{result.max_score}")
                test_results_str = "; ".join(results_list)
            else:
                test_results_str = "Тесты не пройдены"
            
            data.append({
                'ID': app.id,
                'Кандидат': app.candidate.full_name,
                'Вакансия': app.vacancy.title,
                'Департамент': app.vacancy.department.name,
                'Статус': APPLICATION_STATUSES.get(app.status, app.status),
                'Дата подачи': format_datetime(app.created_at),
                'Результаты тестов': test_results_str,
                'Решение HR': app.hr_decision or 'Не принято',
                'Решение департамента': app.dept_decision or 'Не принято',
                'Финальное решение': app.final_decision or 'Не принято'
            })
        
        df = pd.DataFrame(data)
        return df
    except ImportError:
        return None

def validate_magic_token(token):
    """Проверка валидности магической ссылки"""
    from models import CommissionVote
    
    vote = CommissionVote.query.filter_by(magic_token=token, token_used=False).first()
    return vote 

def get_test_questions_count(test):
    """Получение количества вопросов в тесте"""
    if not test or not test.questions:
        return 0
    try:
        questions = json.loads(test.questions)
        return len(questions) if isinstance(questions, list) else 0
    except (json.JSONDecodeError, TypeError):
        return 0

def is_test_required_for_vacancy(test, vacancy):
    """Проверяет, требуется ли тест для данной вакансии"""
    return test in vacancy.required_tests

def get_all_required_tests_for_vacancy(vacancy):
    """Получает все требуемые тесты для вакансии"""
    return list(vacancy.required_tests)

def check_all_tests_completed_for_application(application):
    """Проверяет, пройдены ли все тесты для заявки"""
    from models import TestResult
    
    # Получаем все требуемые тесты
    required_tests = application.vacancy.required_tests
    
    # Проверяем новые тесты
    for test in required_tests:
        result = TestResult.query.filter_by(
            application_id=application.id,
            test_id=test.id
        ).first()
        if not result:
            return False
    
    return True

def get_test_results_for_application(application):
    """Получает результаты тестов для заявки"""
    from models import TestResult
    
    return TestResult.query.filter_by(application_id=application.id).all()

def get_test_result_by_test_id(application, test_id):
    """Получает результат конкретного теста для заявки"""
    from models import TestResult
    
    return TestResult.query.filter_by(
        application_id=application.id,
        test_id=test_id
    ).first() 