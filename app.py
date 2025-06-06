from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
import json
import os
from io import BytesIO
import tempfile
from urllib.parse import unquote

from models import db, User, Department, Vacancy, Application, Test, CommissionVote, TestResult
from utils import (
    APPLICATION_STATUSES, USER_ROLES, EDUCATION_LEVELS, EMPLOYMENT_TYPES, WORK_FORMATS,
    send_email, send_interview_invitation, send_revision_notification, save_uploaded_file, save_pdf_files, log_action,
    calculate_test_score, get_test_questions, format_json_field, get_file_list_from_json, format_date,
    format_datetime, get_status_badge_class, export_applications_to_excel,
    validate_magic_token, get_test_questions_count, is_test_required_for_vacancy,
    get_all_required_tests_for_vacancy, check_all_tests_completed_for_application, moment,
    get_test_results_for_application, get_test_result_by_test_id
)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///university_hr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

# Инициализация базы данных
db.init_app(app)

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Декораторы для проверки ролей
def role_required(role):
    def decorator(f):
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash('У вас нет прав доступа к этой странице.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        decorated_function.__name__ = f.__name__
        return decorated_function
    return decorator

# Главная страница
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'hr':
            return redirect(url_for('hr_dashboard'))
        elif current_user.role == 'department_head':
            return redirect(url_for('dept_dashboard'))
        elif current_user.role == 'candidate':
            return redirect(url_for('candidate_dashboard'))
    
    # Показываем публичные вакансии
    vacancies = Vacancy.query.filter_by(is_active=True).filter(
        Vacancy.application_start <= datetime.utcnow(),
        Vacancy.application_end >= datetime.utcnow()
    ).all()
    
    return render_template('index.html', vacancies=vacancies)

# Вход в систему
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if user and user.check_password(password):
            login_user(user)
            log_action(user.id, 'login', 'user')
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            return redirect(url_for('index'))
        else:
            flash('Неверный email или пароль.', 'error')
    
    return render_template('login.html')

# Выход из системы
@app.route('/logout')
@login_required
def logout():
    log_action(current_user.id, 'logout', 'user')
    logout_user()
    return redirect(url_for('index'))

# Регистрация кандидата
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        middle_name = request.form.get('middle_name', '')
        
        # Проверяем, не существует ли пользователь
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.', 'error')
            return render_template('register.html')
        
        # Создаем нового кандидата
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            role='candidate'
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        log_action(user.id, 'register', 'user')
        flash('Регистрация успешно завершена! Войдите в систему.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Публичные страницы вакансий
@app.route('/vacancies')
def public_vacancies():
    """Публичная страница со всеми активными вакансиями"""
    page = request.args.get('page', 1, type=int)
    department_filter = request.args.get('department')
    education_filter = request.args.get('education_level')
    employment_filter = request.args.get('employment_type')
    
    # Базовый запрос - только активные вакансии в период приема заявок
    query = Vacancy.query.filter_by(is_active=True).filter(
        Vacancy.application_start <= datetime.utcnow(),
        Vacancy.application_end >= datetime.utcnow()
    )
    
    # Применяем фильтры
    if department_filter:
        query = query.filter(Vacancy.department_id == department_filter)
    if education_filter:
        query = query.filter(Vacancy.education_level == education_filter)
    if employment_filter:
        query = query.filter(Vacancy.employment_type == employment_filter)
    
    # Пагинация
    vacancies = query.order_by(Vacancy.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Данные для фильтров
    departments = Department.query.all()
    
    return render_template('public/vacancies.html', 
                         vacancies=vacancies,
                         departments=departments,
                         EDUCATION_LEVELS=EDUCATION_LEVELS,
                         EMPLOYMENT_TYPES=EMPLOYMENT_TYPES,
                         WORK_FORMATS=WORK_FORMATS,
                         selected_department=department_filter,
                         selected_education=education_filter,
                         selected_employment=employment_filter)

@app.route('/vacancies/<int:vacancy_id>')
def public_vacancy_detail(vacancy_id):
    """Публичная страница с детальной информацией о вакансии"""
    vacancy = Vacancy.query.filter_by(id=vacancy_id, is_active=True).first_or_404()
    
    # Проверяем, что вакансия в периоде приема заявок
    now = datetime.utcnow()
    if not (vacancy.application_start <= now <= vacancy.application_end):
        flash('Прием заявок на эту вакансию завершен.', 'warning')
    
    # Проверяем, подавал ли текущий пользователь заявку (если авторизован)
    user_application = None
    if current_user.is_authenticated and current_user.role == 'candidate':
        user_application = Application.query.filter_by(
            vacancy_id=vacancy_id,
            candidate_id=current_user.id
        ).first()
    
    return render_template('public/vacancy_detail.html', 
                         vacancy=vacancy,
                         user_application=user_application,
                         APPLICATION_STATUSES=APPLICATION_STATUSES)

@app.route('/candidate/vacancies')
@login_required
@role_required('candidate')
def candidate_vacancies():
    """Страница вакансий для авторизованных кандидатов"""
    page = request.args.get('page', 1, type=int)
    department_filter = request.args.get('department')
    education_filter = request.args.get('education_level')
    employment_filter = request.args.get('employment_type')
    
    # Базовый запрос - только активные вакансии в период приема заявок
    query = Vacancy.query.filter_by(is_active=True).filter(
        Vacancy.application_start <= datetime.utcnow(),
        Vacancy.application_end >= datetime.utcnow()
    )
    
    # Применяем фильтры
    if department_filter:
        query = query.filter(Vacancy.department_id == department_filter)
    if education_filter:
        query = query.filter(Vacancy.education_level == education_filter)
    if employment_filter:
        query = query.filter(Vacancy.employment_type == employment_filter)
    
    # Пагинация
    vacancies = query.order_by(Vacancy.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    # Получаем ID вакансий, на которые уже подали заявку
    applied_vacancy_ids = [app.vacancy_id for app in current_user.applications]
    
    # Данные для фильтров
    departments = Department.query.all()
    
    return render_template('candidate/vacancies.html', 
                         vacancies=vacancies,
                         applied_vacancy_ids=applied_vacancy_ids,
                         departments=departments,
                         EDUCATION_LEVELS=EDUCATION_LEVELS,
                         EMPLOYMENT_TYPES=EMPLOYMENT_TYPES,
                         WORK_FORMATS=WORK_FORMATS,
                         selected_department=department_filter,
                         selected_education=education_filter,
                         selected_employment=employment_filter)

# Панель администратора
@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    users_count = User.query.count()
    departments_count = Department.query.count()
    vacancies_count = Vacancy.query.count()
    applications_count = Application.query.count()
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         users_count=users_count,
                         departments_count=departments_count,
                         vacancies_count=vacancies_count,
                         applications_count=applications_count,
                         recent_users=recent_users)

# Управление пользователями (админ)
@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users, USER_ROLES=USER_ROLES)

@app.route('/admin/users/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_create_user():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        middle_name = request.form.get('middle_name', '')
        role = request.form['role']
        department_id = request.form.get('department_id') or None
        
        # Проверяем уникальность email
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.', 'error')
            departments = Department.query.all()
            return render_template('admin/create_user.html', departments=departments, USER_ROLES=USER_ROLES)
        
        # Валидация для главы департамента
        if role == 'department_head':
            if not department_id:
                flash('Для главы департамента необходимо выбрать департамент.', 'error')
                departments = Department.query.all()
                return render_template('admin/create_user.html', departments=departments, USER_ROLES=USER_ROLES)
            
            # Проверяем, есть ли уже глава у этого департамента
            department = Department.query.get(department_id)
            if department and department.head_id:
                old_head = User.query.get(department.head_id)
                flash(f'Департамент "{department.name}" уже имеет главу: {old_head.full_name}. Новый пользователь заменит его на посту главы.', 'warning')
        
        # Создаем пользователя
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
        db.session.flush()  # Получаем ID пользователя
        
        # Если создается глава департамента, обновляем департамент
        if role == 'department_head' and department_id:
            department = Department.query.get(department_id)
            if department:
                department.head_id = user.id
        
        db.session.commit()
        
        log_action(current_user.id, 'create_user', 'user', user.id)
        success_msg = 'Пользователь успешно создан.'
        if role == 'department_head':
            success_msg += f' Назначен главой департамента "{department.name}".'
        flash(success_msg, 'success')
        return redirect(url_for('admin_users'))
    
    departments = Department.query.all()
    return render_template('admin/create_user.html', departments=departments, USER_ROLES=USER_ROLES)

@app.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        old_role = user.role
        old_department_id = user.department_id
        
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.middle_name = request.form.get('middle_name', '')
        user.email = request.form['email']
        user.role = request.form['role']
        user.department_id = request.form.get('department_id') or None
        
        # Проверяем уникальность email
        existing_user = User.query.filter_by(email=user.email).first()
        if existing_user and existing_user.id != user.id:
            flash('Пользователь с таким email уже существует.', 'error')
            return render_template('admin/edit_user.html', 
                                 user=user, 
                                 departments=Department.query.all(), 
                                 USER_ROLES=USER_ROLES)
        
        # Валидация для главы департамента
        if user.role == 'department_head':
            if not user.department_id:
                flash('Для главы департамента необходимо выбрать департамент.', 'error')
                return render_template('admin/edit_user.html', 
                                     user=user, 
                                     departments=Department.query.all(), 
                                     USER_ROLES=USER_ROLES)
        
        # Изменяем пароль только если он указан
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)
        
        # Обрабатываем изменения ролей и департаментов
        messages = []
        
        # Если пользователь был главой департамента, убираем его с поста
        if old_role == 'department_head' and old_department_id:
            old_department = Department.query.get(old_department_id)
            if old_department and old_department.head_id == user.id:
                old_department.head_id = None
                messages.append(f'Пользователь снят с поста главы департамента "{old_department.name}".')
        
        # Если пользователь становится главой департамента
        if user.role == 'department_head' and user.department_id:
            department = Department.query.get(user.department_id)
            if department:
                # Проверяем, есть ли уже глава у этого департамента
                if department.head_id and department.head_id != user.id:
                    old_head = User.query.get(department.head_id)
                    messages.append(f'Предыдущий глава департамента "{department.name}" ({old_head.full_name}) заменен.')
                
                department.head_id = user.id
                messages.append(f'Пользователь назначен главой департамента "{department.name}".')
        
        db.session.commit()
        
        log_action(current_user.id, 'edit_user', 'user', user.id)
        
        success_msg = 'Пользователь успешно обновлен.'
        if messages:
            success_msg += ' ' + ' '.join(messages)
        flash(success_msg, 'success')
        return redirect(url_for('admin_users'))
    
    departments = Department.query.all()
    return render_template('admin/edit_user.html', 
                         user=user, 
                         departments=departments, 
                         USER_ROLES=USER_ROLES)

@app.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def admin_toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Нельзя деактивировать самого себя
    if user.id == current_user.id:
        flash('Вы не можете деактивировать собственную учетную запись.', 'error')
        return redirect(url_for('admin_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    log_action(current_user.id, 'toggle_user', 'user', user_id)
    
    status = 'активирован' if user.is_active else 'деактивирован'
    flash(f'Пользователь "{user.full_name}" {status}.', 'success')
    
    return redirect(url_for('admin_users'))

# Управление департаментами (админ)
@app.route('/admin/departments')
@login_required
@role_required('admin')
def admin_departments():
    departments = Department.query.all()
    
    # Подсчитываем количества заранее
    departments_data = []
    for dept in departments:
        # Используем len() для списков или делаем отдельные запросы
        users_count = User.query.filter_by(department_id=dept.id).count()
        vacancies_count = Vacancy.query.filter_by(department_id=dept.id).count()
        
        dept_data = {
            'department': dept,
            'users_count': users_count,
            'vacancies_count': vacancies_count
        }
        departments_data.append(dept_data)
    
    return render_template('admin/departments.html', departments_data=departments_data)

@app.route('/admin/departments/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_create_department():
    if request.method == 'POST':
        name = request.form['name']
        head_id = request.form.get('head_id') or None
        
        department = Department(name=name, head_id=head_id)
        db.session.add(department)
        db.session.commit()
        
        log_action(current_user.id, 'create_department', 'department', department.id)
        flash('Департамент успешно создан.', 'success')
        return redirect(url_for('admin_departments'))
    
    # Только пользователи с ролью department_head
    potential_heads = User.query.filter_by(role='department_head').all()
    return render_template('admin/create_department.html', potential_heads=potential_heads)

@app.route('/admin/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_edit_department(dept_id):
    department = Department.query.get_or_404(dept_id)
    
    if request.method == 'POST':
        department.name = request.form['name']
        head_id = request.form.get('head_id') or None
        department.head_id = head_id
        
        db.session.commit()
        
        log_action(current_user.id, 'edit_department', 'department', department.id)
        flash('Департамент успешно обновлен.', 'success')
        return redirect(url_for('admin_departments'))
    
    # Подсчитываем количества для отображения
    users_count = User.query.filter_by(department_id=department.id).count()
    vacancies_count = Vacancy.query.filter_by(department_id=department.id).count()
    
    # Только пользователи с ролью department_head
    potential_heads = User.query.filter_by(role='department_head').all()
    return render_template('admin/edit_department.html', 
                         department=department, 
                         users_count=users_count,
                         vacancies_count=vacancies_count,
                         potential_heads=potential_heads)

@app.route('/admin/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_department(dept_id):
    department = Department.query.get_or_404(dept_id)
    
    # Проверяем, что в департаменте нет пользователей и вакансий
    users_count = User.query.filter_by(department_id=department.id).count()
    vacancies_count = Vacancy.query.filter_by(department_id=department.id).count()
    
    if users_count > 0:
        flash('Нельзя удалить департамент, в котором есть сотрудники.', 'error')
        return redirect(url_for('admin_departments'))
    
    if vacancies_count > 0:
        flash('Нельзя удалить департамент, в котором есть вакансии.', 'error')
        return redirect(url_for('admin_departments'))
    
    dept_name = department.name
    db.session.delete(department)
    db.session.commit()
    
    log_action(current_user.id, 'delete_department', 'department', dept_id)
    flash(f'Департамент "{dept_name}" успешно удален.', 'success')
    
    return redirect(url_for('admin_departments'))

# Панель HR
@app.route('/hr')
@login_required
@role_required('hr')
def hr_dashboard():
    total_vacancies = Vacancy.query.filter_by(created_by=current_user.id).count()
    total_applications = Application.query.join(Vacancy).filter(Vacancy.created_by == current_user.id).count()
    pending_applications = Application.query.join(Vacancy).filter(
        Vacancy.created_by == current_user.id,
        Application.status == 'pending'
    ).count()
    
    recent_applications = Application.query.join(Vacancy).filter(
        Vacancy.created_by == current_user.id
    ).order_by(Application.created_at.desc()).limit(5).all()
    
    return render_template('hr/dashboard.html',
                         total_vacancies=total_vacancies,
                         total_applications=total_applications,
                         pending_applications=pending_applications,
                         recent_applications=recent_applications)

# Управление вакансиями (HR)
@app.route('/hr/vacancies')
@login_required
@role_required('hr')
def hr_vacancies():
    vacancies = Vacancy.query.filter_by(created_by=current_user.id).all()
    return render_template('hr/vacancies.html', vacancies=vacancies)

@app.route('/hr/vacancies/create', methods=['GET', 'POST'])
@login_required
@role_required('hr')
def hr_create_vacancy():
    if request.method == 'POST':
        # Создание новой вакансии
        vacancy = Vacancy(
            title=request.form['title'],
            department_id=request.form['department_id'],
            discipline=request.form['discipline'],
            employment_type=request.form['employment_type'],
            work_format=request.form['work_format'],
            contract_duration=request.form.get('contract_duration'),
            salary=request.form.get('salary'),
            education_level=request.form['education_level'],
            required_specialty=request.form.get('required_specialty'),
            min_experience=int(request.form.get('min_experience', 0)),
            additional_skills=request.form.get('additional_skills'),
            scientific_activity_level=request.form.get('scientific_activity_level'),
            application_start=datetime.strptime(request.form['application_start'], '%Y-%m-%dT%H:%M'),
            application_end=datetime.strptime(request.form['application_end'], '%Y-%m-%dT%H:%M'),
            work_start_date=datetime.strptime(request.form['work_start_date'], '%Y-%m-%d') if request.form.get('work_start_date') else None,
            created_by=current_user.id,
            contact_person=request.form.get('contact_person'),
            contact_email=request.form.get('contact_email'),
            contact_phone=request.form.get('contact_phone'),
            description=request.form.get('description')
        )
        
        db.session.add(vacancy)
        db.session.flush()  # Получаем ID вакансии
        
        # Добавляем выбранные тесты
        selected_test_ids = request.form.getlist('required_tests')
        if selected_test_ids:
            selected_tests = Test.query.filter(Test.id.in_(selected_test_ids)).all()
            vacancy.required_tests.extend(selected_tests)
        
        db.session.commit()
        
        log_action(current_user.id, 'create_vacancy', 'vacancy', vacancy.id)
        flash('Вакансия успешно создана.', 'success')
        return redirect(url_for('hr_vacancies'))
    
    departments = Department.query.all()
    tests = Test.query.filter_by(created_by=current_user.id, is_active=True).all()
    return render_template('hr/create_vacancy.html', 
                         departments=departments, 
                         tests=tests,
                         EDUCATION_LEVELS=EDUCATION_LEVELS,
                         EMPLOYMENT_TYPES=EMPLOYMENT_TYPES,
                         WORK_FORMATS=WORK_FORMATS)

@app.route('/hr/vacancies/<int:vacancy_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('hr')
def hr_edit_vacancy(vacancy_id):
    vacancy = Vacancy.query.filter_by(id=vacancy_id, created_by=current_user.id).first_or_404()
    
    if request.method == 'POST':
        # Обновление вакансии
        vacancy.title = request.form['title']
        vacancy.department_id = request.form['department_id']
        vacancy.discipline = request.form['discipline']
        vacancy.employment_type = request.form['employment_type']
        vacancy.work_format = request.form['work_format']
        vacancy.contract_duration = request.form.get('contract_duration')
        vacancy.salary = request.form.get('salary')
        vacancy.education_level = request.form['education_level']
        vacancy.required_specialty = request.form.get('required_specialty')
        vacancy.min_experience = int(request.form.get('min_experience', 0))
        vacancy.additional_skills = request.form.get('additional_skills')
        vacancy.scientific_activity_level = request.form.get('scientific_activity_level')
        vacancy.application_start = datetime.strptime(request.form['application_start'], '%Y-%m-%dT%H:%M')
        vacancy.application_end = datetime.strptime(request.form['application_end'], '%Y-%m-%dT%H:%M')
        vacancy.work_start_date = datetime.strptime(request.form['work_start_date'], '%Y-%m-%d') if request.form.get('work_start_date') else None
        vacancy.contact_person = request.form.get('contact_person')
        vacancy.contact_email = request.form.get('contact_email')
        vacancy.contact_phone = request.form.get('contact_phone')
        vacancy.description = request.form.get('description')
        vacancy.updated_at = datetime.utcnow()
        
        # Обновляем связанные тесты
        vacancy.required_tests.clear()  # Очищаем текущие связи
        selected_test_ids = request.form.getlist('required_tests')
        if selected_test_ids:
            selected_tests = Test.query.filter(Test.id.in_(selected_test_ids)).all()
            vacancy.required_tests.extend(selected_tests)
        
        db.session.commit()
        
        log_action(current_user.id, 'edit_vacancy', 'vacancy', vacancy.id)
        flash('Вакансия успешно обновлена.', 'success')
        return redirect(url_for('hr_vacancies'))
    
    departments = Department.query.all()
    tests = Test.query.filter_by(created_by=current_user.id, is_active=True).all()
    current_test_ids = [test.id for test in vacancy.required_tests]
    
    return render_template('hr/edit_vacancy.html', 
                         vacancy=vacancy,
                         departments=departments, 
                         tests=tests,
                         current_test_ids=current_test_ids,
                         EDUCATION_LEVELS=EDUCATION_LEVELS,
                         EMPLOYMENT_TYPES=EMPLOYMENT_TYPES,
                         WORK_FORMATS=WORK_FORMATS)

@app.route('/hr/vacancies/<int:vacancy_id>/toggle', methods=['POST'])
@login_required
@role_required('hr')
def hr_toggle_vacancy(vacancy_id):
    vacancy = Vacancy.query.filter_by(id=vacancy_id, created_by=current_user.id).first_or_404()
    
    # Проверяем, можно ли деактивировать вакансию (есть ли активные заявки)
    if vacancy.is_active and vacancy.applications.filter(Application.status.in_(['pending', 'hr_review', 'dept_review', 'interview_scheduled', 'voting'])).count() > 0:
        flash('Нельзя деактивировать вакансию с активными заявками. Сначала завершите обработку всех заявок.', 'error')
        return redirect(url_for('hr_vacancies'))
    
    vacancy.is_active = not vacancy.is_active
    vacancy.updated_at = datetime.utcnow()
    
    db.session.commit()
    log_action(current_user.id, 'toggle_vacancy', 'vacancy', vacancy_id)
    
    status = 'активирована' if vacancy.is_active else 'деактивирована'
    flash(f'Вакансия "{vacancy.title}" {status}.', 'success')
    
    return redirect(url_for('hr_vacancies'))

# Управление заявками (HR)
@app.route('/hr/applications')
@login_required
@role_required('hr')
def hr_applications():
    status_filter = request.args.get('status')
    department_filter = request.args.get('department')
    vacancy_filter = request.args.get('vacancy_id')  # Добавляем фильтр по вакансии
    
    query = Application.query.join(Vacancy).filter(Vacancy.created_by == current_user.id)
    
    if status_filter:
        query = query.filter(Application.status == status_filter)
    if department_filter:
        query = query.filter(Vacancy.department_id == department_filter)
    if vacancy_filter:  # Фильтр по конкретной вакансии
        query = query.filter(Application.vacancy_id == vacancy_filter)
    
    applications = query.order_by(Application.created_at.desc()).all()
    departments = Department.query.all()
    
    # Получаем информацию о выбранной вакансии для заголовка
    selected_vacancy = None
    if vacancy_filter:
        selected_vacancy = Vacancy.query.filter_by(id=vacancy_filter, created_by=current_user.id).first()
    
    return render_template('hr/applications.html', 
                         applications=applications,
                         departments=departments,
                         selected_vacancy=selected_vacancy,
                         APPLICATION_STATUSES=APPLICATION_STATUSES,
                         selected_status=status_filter,
                         selected_department=department_filter,
                         selected_vacancy_id=vacancy_filter)

@app.route('/hr/applications/<int:app_id>')
@login_required
@role_required('hr')
def hr_view_application(app_id):
    application = Application.query.join(Vacancy).filter(
        Application.id == app_id,
        Vacancy.created_by == current_user.id
    ).first_or_404()
    
    # Получаем результаты голосования
    votes = CommissionVote.query.filter_by(application_id=app_id, token_used=True).all()
    
    # Получаем результаты тестов
    test_results = TestResult.query.filter_by(application_id=app_id).all()
    
    # Создаем словарь результатов тестов для удобного доступа
    test_results_dict = {}
    for result in test_results:
        test_results_dict[result.test_id] = result
    
    # Получаем список глав департаментов
    department_heads = User.query.filter_by(role='department_head', is_active=True).all()
    
    return render_template('hr/view_application.html', 
                         application=application,
                         votes=votes,
                         test_results=test_results_dict,
                         department_heads=department_heads,
                         APPLICATION_STATUSES=APPLICATION_STATUSES)

@app.route('/hr/applications/<int:app_id>/update', methods=['POST'])
@login_required
@role_required('hr')
def hr_update_application(app_id):
    application = Application.query.join(Vacancy).filter(
        Application.id == app_id,
        Vacancy.created_by == current_user.id
    ).first_or_404()
    
    action = request.form['action']
    notes = request.form.get('hr_notes', '').strip()
    
    # Проверяем, что комментарий обязательно заполнен
    if not notes:
        flash('Необходимо обязательно указать обоснование вашего решения.', 'error')
        return redirect(url_for('hr_view_application', app_id=app_id))
    
    if len(notes) < 10:
        flash('Комментарий должен содержать минимум 10 символов.', 'error')
        return redirect(url_for('hr_view_application', app_id=app_id))
    
    if action == 'approve':
        application.hr_decision = 'approve'
        application.status = 'dept_review'
        application.hr_notes = notes
        application.hr_decision_date = datetime.utcnow()
        
        # Обязательно назначаем главу департамента
        dept_head_id = request.form.get('dept_head_id')
        if dept_head_id:
            application.reviewed_by_dept_head = int(dept_head_id)
        else:
            flash('Необходимо выбрать главу департамента для рассмотрения заявки.', 'error')
            return redirect(url_for('hr_view_application', app_id=app_id))
        
    elif action == 'reject':
        application.hr_decision = 'reject'
        application.status = 'rejected'
        application.hr_notes = notes
        application.hr_decision_date = datetime.utcnow()
        
    elif action == 'request_revision':
        application.hr_decision = 'request_revision'
        application.status = 'revision_requested'
        application.revision_requested = True
        application.revision_notes = notes
        application.revision_requested_date = datetime.utcnow()
        application.revision_count = (application.revision_count or 0) + 1
        application.hr_decision_date = datetime.utcnow()
        
        # Отправляем уведомление кандидату
        send_revision_notification(application)
    
    db.session.commit()
    log_action(current_user.id, f'hr_{action}', 'application', app_id)
    
    flash('Заявка успешно обновлена.', 'success')
    return redirect(url_for('hr_view_application', app_id=app_id))

@app.route('/hr/applications/<int:app_id>/schedule_interview', methods=['POST'])
@login_required
@role_required('hr')
def hr_schedule_interview(app_id):
    application = Application.query.join(Vacancy).filter(
        Application.id == app_id,
        Vacancy.created_by == current_user.id
    ).first_or_404()
    
    interview_date = datetime.strptime(request.form['interview_date'], '%Y-%m-%dT%H:%M')
    interview_format = request.form['interview_format']
    interview_link = request.form.get('interview_link', '')
    interview_address = request.form.get('interview_address', '')
    commission_emails = request.form['commission_emails'].split(',')
    commission_emails = [email.strip() for email in commission_emails if email.strip()]
    
    application.interview_date = interview_date
    application.interview_format = interview_format
    application.interview_link = interview_link
    application.interview_address = interview_address
    application.status = 'interview_scheduled'
    
    db.session.commit()
    
    # Отправляем приглашения комиссии
    send_interview_invitation(application, commission_emails)
    
    log_action(current_user.id, 'schedule_interview', 'application', app_id)
    flash('Интервью назначено и приглашения отправлены.', 'success')
    
    return redirect(url_for('hr_view_application', app_id=app_id))

# Управление тестами (HR)
@app.route('/hr/tests')
@login_required
@role_required('hr')
def hr_tests():
    tests = Test.query.filter_by(created_by=current_user.id).all()
    return render_template('hr/tests.html', tests=tests)

@app.route('/hr/tests/create', methods=['GET', 'POST'])
@login_required
@role_required('hr')
def hr_create_test():
    if request.method == 'POST':
        name = request.form['name']
        test_creation_type = request.form['test_creation_type']
        
        if test_creation_type == 'standard':
            # Стандартный тест
            test_type = request.form['type']
            questions = get_test_questions(test_type)
            
            test = Test(
                name=name,
                type=test_type,
                questions=json.dumps(questions, ensure_ascii=False),
                created_by=current_user.id
            )
            
        elif test_creation_type == 'custom':
            # Кастомный тест
            questions_data = []
            
            # Получаем данные вопросов из формы
            question_keys = [key for key in request.form.keys() if key.startswith('questions[') and key.endswith('][text]')]
            
            for key in question_keys:
                # Извлекаем индекс вопроса
                import re
                match = re.search(r'questions\[(\d+)\]\[text\]', key)
                if match:
                    q_index = match.group(1)
                    
                    # Получаем текст вопроса
                    question_text = request.form[f'questions[{q_index}][text]']
                    
                    # Получаем варианты ответов
                    options = []
                    option_keys = [k for k in request.form.keys() if k.startswith(f'questions[{q_index}][options][')]
                    option_keys.sort(key=lambda x: int(re.search(r'questions\[\d+\]\[options\]\[(\d+)\]', x).group(1)))
                    
                    for option_key in option_keys:
                        option_text = request.form[option_key]
                        if option_text.strip():  # Только непустые варианты
                            options.append(option_text.strip())
                    
                    # Получаем правильный ответ
                    correct_answer = int(request.form[f'questions[{q_index}][correct]'])
                    
                    # Создаем объект вопроса
                    question_obj = {
                        'question': question_text,
                        'options': options,
                        'correct': correct_answer
                    }
                    
                    questions_data.append(question_obj)
            
            test = Test(
                name=name,
                type='custom',
                questions=json.dumps(questions_data, ensure_ascii=False),
                created_by=current_user.id
            )
        
        else:
            flash('Неверный тип создания теста.', 'error')
            return redirect(url_for('hr_create_test'))
        
        db.session.add(test)
        db.session.commit()
        
        log_action(current_user.id, 'create_test', 'test', test.id)
        flash('Тест успешно создан.', 'success')
        return redirect(url_for('hr_tests'))
    
    return render_template('hr/create_test.html')

@app.route('/hr/tests/<int:test_id>')
@login_required
@role_required('hr')
def hr_view_test(test_id):
    test = Test.query.filter_by(id=test_id, created_by=current_user.id).first_or_404()
    questions = format_json_field(test.questions, [])
    
    return render_template('hr/view_test.html', test=test, questions=questions)

@app.route('/hr/tests/<int:test_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('hr')
def hr_edit_test(test_id):
    test = Test.query.filter_by(id=test_id, created_by=current_user.id).first_or_404()
    
    if request.method == 'POST':
        test.name = request.form['name']
        test.is_active = bool(request.form.get('is_active'))
        
        db.session.commit()
        flash('Тест успешно обновлен.', 'success')
        return redirect(url_for('hr_view_test', test_id=test_id))
    
    return render_template('hr/edit_test.html', test=test)

@app.route('/hr/tests/<int:test_id>/toggle', methods=['POST'])
@login_required
@role_required('hr')
def hr_toggle_test(test_id):
    test = Test.query.filter_by(id=test_id, created_by=current_user.id).first_or_404()
    test.is_active = not test.is_active
    
    db.session.commit()
    log_action(current_user.id, 'toggle_test', 'test', test_id)
    
    status = 'активирован' if test.is_active else 'деактивирован'
    flash(f'Тест {status}.', 'success')
    
    return redirect(url_for('hr_tests'))

# Панель главы департамента
@app.route('/department')
@login_required
@role_required('department_head')
def dept_dashboard():
    # Заявки на рассмотрении у этого главы департамента
    pending_applications = Application.query.filter_by(
        reviewed_by_dept_head=current_user.id,
        status='dept_review'
    ).all()
    
    return render_template('department/dashboard.html', 
                         pending_applications=pending_applications)

@app.route('/department/applications/<int:app_id>')
@login_required
@role_required('department_head')
def dept_view_application(app_id):
    application = Application.query.filter_by(
        id=app_id,
        reviewed_by_dept_head=current_user.id
    ).first_or_404()
    
    # Получаем результаты тестов
    test_results = TestResult.query.filter_by(application_id=app_id).all()
    
    # Создаем словарь результатов тестов для удобного доступа
    test_results_dict = {}
    for result in test_results:
        test_results_dict[result.test_id] = result
    
    return render_template('department/view_application.html', 
                         application=application,
                         test_results=test_results_dict)

@app.route('/department/applications/<int:app_id>/decision', methods=['POST'])
@login_required
@role_required('department_head')
def dept_make_decision(app_id):
    application = Application.query.filter_by(
        id=app_id,
        reviewed_by_dept_head=current_user.id
    ).first_or_404()
    
    decision = request.form['decision']
    notes = request.form.get('dept_notes', '').strip()
    
    # Проверяем, что комментарий обязательно заполнен
    if not notes:
        flash('Необходимо обязательно указать обоснование вашего решения.', 'error')
        return redirect(url_for('dept_view_application', app_id=app_id))
    
    if len(notes) < 10:
        flash('Комментарий должен содержать минимум 10 символов.', 'error')
        return redirect(url_for('dept_view_application', app_id=app_id))
    
    application.dept_decision = decision
    application.dept_notes = notes
    application.dept_decision_date = datetime.utcnow()
    
    if decision == 'recommend':
        application.status = 'hr_review'  # Возвращаем HR для назначения интервью
    else:
        application.status = 'rejected'
    
    db.session.commit()
    log_action(current_user.id, f'dept_{decision}', 'application', app_id)
    
    flash('Решение принято.', 'success')
    return redirect(url_for('dept_dashboard'))

# Панель кандидата
@app.route('/candidate')
@login_required
@role_required('candidate')
def candidate_dashboard():
    applications = Application.query.filter_by(candidate_id=current_user.id).all()
    available_vacancies = Vacancy.query.filter_by(is_active=True).filter(
        Vacancy.application_start <= datetime.utcnow(),
        Vacancy.application_end >= datetime.utcnow()
    ).all()
    
    # Исключаем вакансии, на которые уже подали заявку
    applied_vacancy_ids = [app.vacancy_id for app in applications]
    available_vacancies = [v for v in available_vacancies if v.id not in applied_vacancy_ids]
    
    return render_template('candidate/dashboard.html', 
                         applications=applications,
                         available_vacancies=available_vacancies,
                         APPLICATION_STATUSES=APPLICATION_STATUSES)

@app.route('/candidate/apply/<int:vacancy_id>')
@login_required
@role_required('candidate')
def candidate_apply(vacancy_id):
    vacancy = Vacancy.query.get_or_404(vacancy_id)
    
    # Проверяем, не подавал ли уже заявку
    existing_application = Application.query.filter_by(
        vacancy_id=vacancy_id,
        candidate_id=current_user.id
    ).first()
    
    if existing_application:
        flash('Вы уже подали заявку на эту вакансию.', 'error')
        return redirect(url_for('candidate_dashboard'))
    
    # Ищем последнюю заявку пользователя для предзаполнения формы
    last_application = Application.query.filter_by(
        candidate_id=current_user.id
    ).order_by(Application.created_at.desc()).first()
    
    return render_template('candidate/apply.html', 
                         vacancy=vacancy,
                         last_application=last_application)

@app.route('/candidate/submit_application/<int:vacancy_id>', methods=['POST'])
@login_required
@role_required('candidate')
def candidate_submit_application(vacancy_id):
    vacancy = Vacancy.query.get_or_404(vacancy_id)
    
    # Обработка загружаемых документов
    degree_files = []
    course_certificates = []
    language_certificates = []
    award_documents = []
    
    # Обработка документов об ученой степени
    if 'degree_files' in request.files:
        files = request.files.getlist('degree_files')
        degree_files = save_pdf_files(files, 'uploads/documents/degrees')
    
    # Обработка сертификатов курсов
    if 'course_certificates' in request.files:
        files = request.files.getlist('course_certificates')
        course_certificates = save_pdf_files(files, 'uploads/documents/certificates')
    
    # Обработка сертификатов языков
    if 'language_certificates' in request.files:
        files = request.files.getlist('language_certificates')
        language_certificates = save_pdf_files(files, 'uploads/documents/languages')
    
    # Обработка документов о наградах
    if 'award_documents' in request.files:
        files = request.files.getlist('award_documents')
        award_documents = save_pdf_files(files, 'uploads/documents/awards')
    
    # Создаем новую заявку
    application = Application(
        vacancy_id=vacancy_id,
        candidate_id=current_user.id,
        birth_date=datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date() if request.form.get('birth_date') else None,
        citizenship=request.form.get('citizenship'),
        city=request.form.get('city'),
        phone=request.form.get('phone'),
        marital_status=request.form.get('marital_status'),
        military_status=request.form.get('military_status'),
        no_criminal_record=bool(request.form.get('no_criminal_record')),
        has_disability=bool(request.form.get('has_disability')),
        is_pensioner=bool(request.form.get('is_pensioner')),
        work_experience=request.form.get('work_experience'),
        academic_degree=request.form.get('academic_degree'),
        academic_title=request.form.get('academic_title'),
        title_date=datetime.strptime(request.form['title_date'], '%Y-%m-%d').date() if request.form.get('title_date') else None,
        publications_count=int(request.form.get('publications_count', 0)),
        key_publications=request.form.get('key_publications'),
        projects_count=int(request.form.get('projects_count', 0)),
        projects_list=request.form.get('projects_list'),
        h_index=int(request.form.get('h_index', 0)) if request.form.get('h_index') else None,
        patents=request.form.get('patents'),
        courses=request.form.get('courses'),
        languages=request.form.get('languages'),
        awards=request.form.get('awards'),
        video_presentation=request.form.get('video_presentation'),
        # Сохраняем пути к загруженным документам
        degree_files=json.dumps(degree_files) if degree_files else None,
        course_certificates=json.dumps(course_certificates) if course_certificates else None,
        language_certificates=json.dumps(language_certificates) if language_certificates else None,
        award_documents=json.dumps(award_documents) if award_documents else None,
        data_processing_consent=bool(request.form.get('data_processing_consent')),
        video_audio_consent=bool(request.form.get('video_audio_consent'))
    )
    
    db.session.add(application)
    db.session.commit()
    
    log_action(current_user.id, 'submit_application', 'application', application.id)
    flash('Заявка успешно подана. Теперь необходимо пройти тесты.', 'success')
    
    return redirect(url_for('candidate_take_tests', app_id=application.id))

@app.route('/candidate/tests/<int:app_id>')
@login_required
@role_required('candidate')
def candidate_take_tests(app_id):
    application = Application.query.filter_by(
        id=app_id,
        candidate_id=current_user.id
    ).first_or_404()
    
    # Получаем все результаты тестов для этой заявки
    completed_test_results = TestResult.query.filter_by(application_id=app_id).all()
    completed_test_ids = [result.test_id for result in completed_test_results if result.test_id]
    
    # Получаем требуемые тесты
    required_tests = application.vacancy.required_tests
    
    # Фильтруем тесты, которые еще не пройдены
    tests_to_take = []
    for test in required_tests:
        if test.id not in completed_test_ids:
            tests_to_take.append(test)
    
    return render_template('candidate/tests.html', 
                         application=application,
                         tests_to_take=tests_to_take)

@app.route('/candidate/test/<int:app_id>/<int:test_id>')
@login_required
@role_required('candidate')
def candidate_take_test(app_id, test_id):
    application = Application.query.filter_by(
        id=app_id,
        candidate_id=current_user.id
    ).first_or_404()
    
    test = Test.query.get_or_404(test_id)
    
    # Проверяем, что этот тест требуется для вакансии
    if test not in application.vacancy.required_tests:
        flash('Этот тест не требуется для данной вакансии.', 'error')
        return redirect(url_for('candidate_dashboard'))
    
    # Проверяем, не пройден ли уже тест
    existing_result = TestResult.query.filter_by(
        application_id=app_id,
        test_id=test_id
    ).first()
    
    if existing_result:
        flash('Этот тест уже пройден.', 'info')
        return redirect(url_for('candidate_take_tests', app_id=app_id))
    
    # Получаем вопросы
    questions = format_json_field(test.questions, [])
    
    return render_template('candidate/test.html', 
                         application=application,
                         test=test,
                         questions=questions)

@app.route('/candidate/submit_test/<int:app_id>/<int:test_id>', methods=['POST'])
@login_required
@role_required('candidate')
def candidate_submit_test_new(app_id, test_id):
    application = Application.query.filter_by(
        id=app_id,
        candidate_id=current_user.id
    ).first_or_404()
    
    test = Test.query.get_or_404(test_id)
    
    # Проверяем, что этот тест требуется для вакансии
    if test not in application.vacancy.required_tests:
        flash('Этот тест не требуется для данной вакансии.', 'error')
        return redirect(url_for('candidate_dashboard'))
    
    questions = format_json_field(test.questions, [])
    answers = []
    correct_answers = []
    
    for i, question in enumerate(questions):
        answer = request.form.get(f'question_{i}')
        if answer is not None:
            answers.append(int(answer))
            correct_answers.append(question['correct'])
    
    score = calculate_test_score(answers, correct_answers)
    
    # Создаем запись результата теста
    test_result = TestResult(
        application_id=app_id,
        test_id=test_id,
        test_type=test.type,
        answers=json.dumps(answers),
        score=score,
        max_score=len(questions)
    )
    
    db.session.add(test_result)
    db.session.commit()
    
    log_action(current_user.id, f'complete_test_{test_id}', 'test_result', test_result.id)
    
    # Проверяем, все ли тесты пройдены
    completed_test_results = TestResult.query.filter_by(application_id=app_id).all()
    completed_test_ids = [result.test_id for result in completed_test_results if result.test_id]
    required_test_ids = [t.id for t in application.vacancy.required_tests]
    
    # Также проверяем новые тесты
    all_tests_completed = True
    
    # Проверяем новые тесты
    for test_id in required_test_ids:
        if test_id not in completed_test_ids:
            all_tests_completed = False
            break
    
    if all_tests_completed:
        application.status = 'hr_review'
        db.session.commit()
        flash('Все тесты пройдены! Ваша заявка отправлена на рассмотрение.', 'success')
    else:
        flash(f'Тест "{test.name}" пройден! Результат: {score}/{len(questions)}', 'success')
    
    return redirect(url_for('candidate_take_tests', app_id=app_id))

# Голосование комиссии (магические ссылки)
@app.route('/vote/<token>')
def commission_vote_page(token):
    vote = validate_magic_token(token)
    
    if not vote:
        return render_template('error.html', 
                             message='Ссылка недействительна или уже использована.')
    
    application = vote.application
    
    # Получаем статистику голосования
    all_votes = CommissionVote.query.filter_by(application_id=application.id).all()
    completed_votes = [v for v in all_votes if v.voted_at is not None]
    
    # Подсчитываем голоса
    approve_votes = sum(1 for v in completed_votes if v.vote == 'approve')
    reject_votes = sum(1 for v in completed_votes if v.vote == 'reject')
    abstain_votes = sum(1 for v in completed_votes if v.vote == 'abstain')
    total_votes = len(completed_votes)
    
    return render_template('commission/vote.html', 
                         vote=vote,
                         application=application,
                         total_votes=total_votes,
                         approve_votes=approve_votes,
                         reject_votes=reject_votes,
                         abstain_votes=abstain_votes)

@app.route('/submit_vote/<token>', methods=['POST'])
def submit_commission_vote(token):
    vote = validate_magic_token(token)
    
    if not vote:
        return render_template('error.html', 
                             message='Ссылка недействительна или уже использована.')
    
    # Получаем данные из формы
    vote_choice = request.form['vote']
    comment = request.form.get('comment', '').strip()
    
    # Проверяем, что комментарий обязательно заполнен
    if not comment:
        flash('Необходимо обязательно указать обоснование вашего решения.', 'error')
        return redirect(url_for('commission_vote_page', token=token))
    
    if len(comment) < 10:
        flash('Комментарий должен содержать минимум 10 символов.', 'error')
        return redirect(url_for('commission_vote_page', token=token))
    
    vote.vote = vote_choice
    vote.justification = comment
    vote.voted_at = datetime.utcnow()
    vote.token_used = True
    
    db.session.commit()
    
    # Проверяем, все ли члены комиссии проголосовали
    total_votes = CommissionVote.query.filter_by(application_id=vote.application_id).count()
    completed_votes = CommissionVote.query.filter_by(
        application_id=vote.application_id,
        token_used=True
    ).count()
    
    if completed_votes == total_votes:
        # Все проголосовали, меняем статус
        application = vote.application
        application.status = 'voting'
        db.session.commit()
    
    return render_template('commission/vote_success.html')

# API для экспорта данных
@app.route('/hr/export/applications')
@login_required
@role_required('hr')
def export_applications():
    applications = Application.query.join(Vacancy).filter(
        Vacancy.created_by == current_user.id
    ).all()
    
    df = export_applications_to_excel(applications)
    if df is not None:
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            df.to_excel(tmp.name, index=False)
            tmp_path = tmp.name
        
        return send_file(tmp_path, 
                        as_attachment=True,
                        download_name=f'applications_{datetime.now().strftime("%Y%m%d")}.xlsx',
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    else:
        flash('Ошибка при экспорте данных. Убедитесь, что установлен pandas.', 'error')
        return redirect(url_for('hr_applications'))

# Контекстные процессоры для шаблонов
@app.context_processor
def utility_processor():
    return dict(
        APPLICATION_STATUSES=APPLICATION_STATUSES,
        USER_ROLES=USER_ROLES,
        EDUCATION_LEVELS=EDUCATION_LEVELS,
        EMPLOYMENT_TYPES=EMPLOYMENT_TYPES,
        WORK_FORMATS=WORK_FORMATS,
        format_date=format_date,
        format_datetime=format_datetime,
        get_status_badge_class=get_status_badge_class,
        format_json_field=format_json_field,
        get_file_list_from_json=get_file_list_from_json,
        get_test_questions_count=get_test_questions_count,
        is_test_required_for_vacancy=is_test_required_for_vacancy,
        get_all_required_tests_for_vacancy=get_all_required_tests_for_vacancy,
        check_all_tests_completed_for_application=check_all_tests_completed_for_application,
        get_test_results_for_application=get_test_results_for_application,
        get_test_result_by_test_id=get_test_result_by_test_id,
        moment=moment
    )

# Добавляем фильтр для Jinja2
@app.template_filter('from_json')
def from_json_filter(value):
    return format_json_field(value, [])

@app.template_filter('nl2br')
def nl2br_filter(value):
    """Заменяет переносы строк на HTML теги <br>"""
    if not value:
        return ''
    return value.replace('\n', '<br>')

@app.template_filter('age')
def age_filter(birth_date):
    """Вычисляет возраст по дате рождения"""
    from utils import calculate_age
    return calculate_age(birth_date)

@app.route('/candidate/my-tests')
@login_required
@role_required('candidate')
def candidate_my_tests():
    """Страница всех тестов кандидата"""
    # Получаем все заявки кандидата
    applications = Application.query.filter_by(candidate_id=current_user.id).all()
    
    # Группируем тесты по статусу
    pending_tests = []
    completed_tests = []
    
    for app in applications:
        for test in app.vacancy.required_tests:
            # Проверяем, пройден ли тест
            test_result = TestResult.query.filter_by(
                application_id=app.id,
                test_id=test.id
            ).first()
            
            test_info = {
                'test': test,
                'application': app,
                'completed': bool(test_result),
                'result': test_result
            }
            
            if test_result:
                completed_tests.append(test_info)
            else:
                pending_tests.append(test_info)
    
    return render_template('candidate/my_tests.html',
                         pending_tests=pending_tests,
                         completed_tests=completed_tests)

@app.route('/hr/applications/<int:app_id>/final_decision', methods=['POST'])
@login_required
@role_required('hr')
def hr_final_decision(app_id):
    application = Application.query.join(Vacancy).filter(
        Application.id == app_id,
        Vacancy.created_by == current_user.id
    ).first_or_404()
    
    # Проверяем, что голосование действительно завершено
    if application.status != 'voting':
        flash('Финальное решение можно принимать только после завершения голосования.', 'error')
        return redirect(url_for('hr_view_application', app_id=app_id))
    
    final_decision = request.form['final_decision']
    final_notes = request.form.get('final_notes', '')
    contract_duration_offered = request.form.get('contract_duration_offered', '')
    
    # Обновляем заявку
    application.final_decision = final_decision
    application.final_notes = final_notes
    application.contract_duration_offered = contract_duration_offered
    application.status = 'approved' if final_decision == 'approved' else 'rejected'
    
    db.session.commit()
    log_action(current_user.id, f'final_decision_{final_decision}', 'application', app_id)
    
    decision_text = 'одобрена' if final_decision == 'approved' else 'отклонена'
    flash(f'Заявка {decision_text}. Принято финальное решение.', 'success')
    
    return redirect(url_for('hr_view_application', app_id=app_id))

@app.route('/admin/email-settings')
@login_required
@role_required('admin')
def admin_email_settings():
    from email_config import get_email_config, get_smtp_providers
    
    email_config = get_email_config()
    smtp_providers = get_smtp_providers()
    
    return render_template('admin/email_settings.html',
                         email_config=email_config,
                         smtp_providers=smtp_providers)

@app.route('/admin/test-email', methods=['POST'])
@login_required
@role_required('admin')
def admin_test_email():
    from email_config import get_email_config
    from utils import send_email
    
    test_email = request.form['test_email']
    test_subject = request.form['test_subject']
    test_message = request.form['test_message']
    
    # Создаем HTML версию сообщения
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{test_subject}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f8f9fa; }}
            .footer {{ background-color: #6c757d; color: white; padding: 15px; text-align: center; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>📧 Тестовое письмо</h2>
                <p>HR Платформа АУЭС</p>
            </div>
            <div class="content">
                <p>{test_message.replace(chr(10), '</p><p>')}</p>
                <p><strong>Время отправки:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
                <p><strong>Отправлено пользователем:</strong> {current_user.full_name} ({current_user.email})</p>
            </div>
            <div class="footer">
                <p>Это тестовое сообщение от HR платформы АУЭС</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    config = get_email_config()
    
    if send_email(test_email, test_subject, html_content):
        if config['TESTING_MODE']:
            flash('Тестовое письмо обработано в тестовом режиме. Проверьте логи консоли.', 'success')
        else:
            flash(f'Тестовое письмо успешно отправлено на {test_email}', 'success')
        log_action(current_user.id, 'test_email', 'email', None, f'Отправлено на {test_email}')
    else:
        flash('Не удалось отправить тестовое письмо. Проверьте настройки SMTP.', 'error')
    
    return redirect(url_for('admin_email_settings'))

@app.route('/hr/applications/<int:app_id>/start_voting', methods=['POST'])
@login_required
@role_required('hr')
def hr_start_voting(app_id):
    application = Application.query.join(Vacancy).filter(
        Application.id == app_id,
        Vacancy.created_by == current_user.id
    ).first_or_404()
    
    if application.status != 'interview_scheduled':
        flash('Переход к голосованию возможен только после назначения интервью.', 'error')
        return redirect(url_for('hr_view_application', app_id=app_id))
    
    # Меняем статус на голосование
    application.status = 'voting'
    db.session.commit()
    
    log_action(current_user.id, 'start_voting', 'application', app_id)
    flash('Этап голосования начат. Комиссия может голосовать по магическим ссылкам.', 'success')
    
    return redirect(url_for('hr_view_application', app_id=app_id))

@app.route('/hr/applications/<int:app_id>/reject')
@login_required
@role_required('hr')
def hr_reject_application(app_id):
    application = Application.query.join(Vacancy).filter(
        Application.id == app_id,
        Vacancy.created_by == current_user.id
    ).first_or_404()
    
    # Отклоняем заявку
    application.status = 'rejected'
    application.final_decision = 'rejected'
    application.final_notes = 'Отклонено HR на этапе назначенного интервью'
    
    db.session.commit()
    
    log_action(current_user.id, 'reject_after_interview', 'application', app_id)
    flash('Заявка отклонена.', 'success')
    
    return redirect(url_for('hr_view_application', app_id=app_id))

@app.route('/candidate/application/<int:app_id>')
@login_required
@role_required('candidate')
def candidate_view_application(app_id):
    """Детальный просмотр заявки кандидатом"""
    application = Application.query.filter_by(
        id=app_id,
        candidate_id=current_user.id
    ).first_or_404()
    
    # Получаем результаты тестов
    test_results = TestResult.query.filter_by(application_id=app_id).all()
    test_results_dict = {}
    for result in test_results:
        test_results_dict[result.test_id] = result
    
    # Получаем результаты голосования (только если статус voting или завершен)
    votes = []
    if application.status in ['voting', 'approved', 'rejected']:
        votes = CommissionVote.query.filter_by(
            application_id=app_id,
            token_used=True
        ).all()
    
    return render_template('candidate/view_application.html', 
                         application=application,
                         test_results=test_results_dict,
                         votes=votes)

@app.route('/candidate/application/<int:app_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('candidate')
def candidate_edit_application(app_id):
    """Редактирование заявки кандидатом после запроса на доработку"""
    application = Application.query.filter_by(
        id=app_id,
        candidate_id=current_user.id
    ).first_or_404()
    
    # Проверяем, что заявка действительно требует доработки
    if application.status != 'revision_requested':
        flash('Заявка не требует доработки.', 'info')
        return redirect(url_for('candidate_view_application', app_id=app_id))
    
    if request.method == 'POST':
        # Обновляем данные заявки
        application.birth_date = datetime.strptime(request.form['birth_date'], '%Y-%m-%d').date() if request.form.get('birth_date') else None
        application.citizenship = request.form.get('citizenship')
        application.city = request.form.get('city')
        application.phone = request.form.get('phone')
        application.marital_status = request.form.get('marital_status')
        application.military_status = request.form.get('military_status')
        application.no_criminal_record = bool(request.form.get('no_criminal_record'))
        application.has_disability = bool(request.form.get('has_disability'))
        application.is_pensioner = bool(request.form.get('is_pensioner'))
        application.work_experience = request.form.get('work_experience')
        application.academic_degree = request.form.get('academic_degree')
        application.academic_title = request.form.get('academic_title')
        application.title_date = datetime.strptime(request.form['title_date'], '%Y-%m-%d').date() if request.form.get('title_date') else None
        application.publications_count = int(request.form.get('publications_count', 0))
        application.key_publications = request.form.get('key_publications')
        application.projects_count = int(request.form.get('projects_count', 0))
        application.projects_list = request.form.get('projects_list')
        application.h_index = int(request.form.get('h_index', 0)) if request.form.get('h_index') else None
        application.patents = request.form.get('patents')
        application.courses = request.form.get('courses')
        application.languages = request.form.get('languages')
        application.awards = request.form.get('awards')
        application.video_presentation = request.form.get('video_presentation')
        
        # Обработка новых документов (если загружены)
        # Обработка документов об ученой степени
        if 'degree_files' in request.files:
            files = request.files.getlist('degree_files')
            new_degree_files = save_pdf_files(files, 'uploads/documents/degrees')
            if new_degree_files:
                existing_files = get_file_list_from_json(application.degree_files)
                existing_files.extend(new_degree_files)
                application.degree_files = json.dumps(existing_files)
        
        # Аналогично для других типов документов
        for doc_type, folder in [
            ('course_certificates', 'uploads/documents/certificates'),
            ('language_certificates', 'uploads/documents/languages'),
            ('award_documents', 'uploads/documents/awards')
        ]:
            if doc_type in request.files:
                files = request.files.getlist(doc_type)
                new_files = save_pdf_files(files, folder)
                if new_files:
                    existing_files = get_file_list_from_json(getattr(application, doc_type))
                    existing_files.extend(new_files)
                    setattr(application, doc_type, json.dumps(existing_files))
        
        # Меняем статус обратно на рассмотрение HR
        application.status = 'hr_review'
        application.revision_requested = False
        application.updated_at = datetime.utcnow()
        
        # Сбрасываем предыдущие решения HR (они будут приняты заново)
        application.hr_decision = None
        application.hr_decision_date = None
        
        db.session.commit()
        
        log_action(current_user.id, 'update_application_after_revision', 'application', application.id)
        flash('Заявка успешно обновлена и отправлена на повторное рассмотрение HR.', 'success')
        return redirect(url_for('candidate_view_application', app_id=app_id))
    
    return render_template('candidate/edit_application.html', application=application)

@app.route('/admin/analytics')
@login_required
@role_required('admin')
def admin_analytics():
    """Аналитика для администратора"""
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta
    
    # Общие метрики
    total_users = User.query.count()
    total_departments = Department.query.count()
    total_vacancies = Vacancy.query.count()
    total_applications = Application.query.count()
    total_tests = Test.query.count()
    
    # Активные пользователи по ролям
    user_roles = db.session.query(
        User.role, 
        func.count(User.id).label('count')
    ).filter_by(is_active=True).group_by(User.role).all()
    
    # Статистика заявок по статусам
    application_statuses = db.session.query(
        Application.status,
        func.count(Application.id).label('count')
    ).group_by(Application.status).all()
    
    # Статистика по департаментам
    department_stats = db.session.query(
        Department.name,
        func.count(Application.id).label('applications'),
        func.count(Vacancy.id).label('vacancies')
    ).outerjoin(Vacancy, Department.id == Vacancy.department_id)\
     .outerjoin(Application, Vacancy.id == Application.vacancy_id)\
     .group_by(Department.id, Department.name).all()
    
    # Статистика тестов
    test_stats = db.session.query(
        Test.type,
        func.count(TestResult.id).label('completed'),
        func.avg(TestResult.score).label('avg_score'),
        func.max(TestResult.max_score).label('max_score')
    ).outerjoin(TestResult, Test.id == TestResult.test_id)\
     .group_by(Test.type).all()
    
    # Динамика заявок за последние 30 дней
    last_30_days = datetime.utcnow() - timedelta(days=30)
    daily_apps_raw = db.session.query(
        func.date(Application.created_at).label('date'),
        func.count(Application.id).label('count')
    ).filter(Application.created_at >= last_30_days)\
     .group_by(func.date(Application.created_at))\
     .order_by(func.date(Application.created_at)).all()
    
    # Преобразуем строки дат в объекты datetime для правильной работы в шаблоне
    daily_applications = []
    for day_raw in daily_apps_raw:
        try:
            # Преобразуем строку даты в объект datetime
            if isinstance(day_raw.date, str):
                date_obj = datetime.strptime(day_raw.date, '%Y-%m-%d').date()
            else:
                date_obj = day_raw.date
                
            daily_applications.append({
                'date': date_obj,
                'count': day_raw.count
            })
        except (ValueError, AttributeError):
            # Если не удается преобразовать дату, пропускаем запись
            continue
    
    # Конверсия по этапам
    conversion_stats = {
        'submitted': Application.query.count(),
        'hr_reviewed': Application.query.filter(Application.hr_decision.isnot(None)).count(),
        'dept_reviewed': Application.query.filter(Application.dept_decision.isnot(None)).count(),
        'interviewed': Application.query.filter(Application.interview_date.isnot(None)).count(),
        'voted': Application.query.filter(Application.status.in_(['voting', 'approved', 'rejected'])).count(),
        'approved': Application.query.filter_by(final_decision='approved').count()
    }
    
    # Топ департаментов по активности
    top_departments = db.session.query(
        Department.name,
        func.count(Application.id).label('applications')
    ).join(Vacancy, Department.id == Vacancy.department_id)\
     .join(Application, Vacancy.id == Application.vacancy_id)\
     .group_by(Department.id, Department.name)\
     .order_by(func.count(Application.id).desc())\
     .limit(5).all()
    
    return render_template('admin/analytics.html',
                         total_users=total_users,
                         total_departments=total_departments,
                         total_vacancies=total_vacancies,
                         total_applications=total_applications,
                         total_tests=total_tests,
                         user_roles=user_roles,
                         application_statuses=application_statuses,
                         department_stats=department_stats,
                         test_stats=test_stats,
                         daily_applications=daily_applications,
                         conversion_stats=conversion_stats,
                         top_departments=top_departments)

@app.route('/hr/analytics')
@login_required
@role_required('hr')
def hr_analytics():
    """Аналитика для HR"""
    from sqlalchemy import func, extract
    from datetime import datetime, timedelta
    
    # Метрики только для вакансий этого HR
    my_vacancies = Vacancy.query.filter_by(created_by=current_user.id)
    my_vacancy_ids = [v.id for v in my_vacancies]
    
    if not my_vacancy_ids:
        # Если у HR нет вакансий, показываем пустую статистику
        return render_template('hr/analytics.html',
                             total_vacancies=0,
                             total_applications=0,
                             application_statuses=[],
                             test_stats=[],
                             daily_applications=[],
                             conversion_stats={},
                             top_candidates=[])
    
    # Общие метрики HR
    total_vacancies = len(my_vacancy_ids)
    total_applications = Application.query.filter(Application.vacancy_id.in_(my_vacancy_ids)).count()
    
    # Статистика заявок по статусам (только для вакансий этого HR)
    application_statuses = db.session.query(
        Application.status,
        func.count(Application.id).label('count')
    ).filter(Application.vacancy_id.in_(my_vacancy_ids))\
     .group_by(Application.status).all()
    
    # Статистика тестов для заявок этого HR
    test_stats = db.session.query(
        Test.name,
        Test.type,
        func.count(TestResult.id).label('completed'),
        func.avg(TestResult.score).label('avg_score'),
        func.max(TestResult.max_score).label('max_score')
    ).join(TestResult, Test.id == TestResult.test_id)\
     .join(Application, TestResult.application_id == Application.id)\
     .filter(Application.vacancy_id.in_(my_vacancy_ids))\
     .group_by(Test.id, Test.name, Test.type).all()
    
    # Динамика заявок за последние 30 дней
    last_30_days = datetime.utcnow() - timedelta(days=30)
    daily_apps_raw = db.session.query(
        func.date(Application.created_at).label('date'),
        func.count(Application.id).label('count')
    ).filter(Application.vacancy_id.in_(my_vacancy_ids))\
     .filter(Application.created_at >= last_30_days)\
     .group_by(func.date(Application.created_at))\
     .order_by(func.date(Application.created_at)).all()
    
    # Преобразуем строки дат в объекты datetime для правильной работы в шаблоне
    daily_applications = []
    for day_raw in daily_apps_raw:
        try:
            # Преобразуем строку даты в объект datetime
            if isinstance(day_raw.date, str):
                date_obj = datetime.strptime(day_raw.date, '%Y-%m-%d').date()
            else:
                date_obj = day_raw.date
                
            daily_applications.append({
                'date': date_obj,
                'count': day_raw.count
            })
        except (ValueError, AttributeError):
            # Если не удается преобразовать дату, пропускаем запись
            continue
    
    # Конверсия по этапам
    base_query = Application.query.filter(Application.vacancy_id.in_(my_vacancy_ids))
    conversion_stats = {
        'submitted': base_query.count(),
        'hr_reviewed': base_query.filter(Application.hr_decision.isnot(None)).count(),
        'dept_reviewed': base_query.filter(Application.dept_decision.isnot(None)).count(),
        'interviewed': base_query.filter(Application.interview_date.isnot(None)).count(),
        'voted': base_query.filter(Application.status.in_(['voting', 'approved', 'rejected'])).count(),
        'approved': base_query.filter_by(final_decision='approved').count()
    }
    
    # Топ кандидатов по результатам тестов
    top_candidates = db.session.query(
        User.first_name,
        User.last_name,
        Vacancy.title,
        func.avg(TestResult.score).label('avg_score'),
        func.count(TestResult.id).label('tests_count')
    ).join(Application, User.id == Application.candidate_id)\
     .join(Vacancy, Application.vacancy_id == Vacancy.id)\
     .join(TestResult, Application.id == TestResult.application_id)\
     .filter(Application.vacancy_id.in_(my_vacancy_ids))\
     .group_by(User.id, User.first_name, User.last_name, Vacancy.title)\
     .having(func.count(TestResult.id) > 0)\
     .order_by(func.avg(TestResult.score).desc())\
     .limit(10).all()
    
    return render_template('hr/analytics.html',
                         total_vacancies=total_vacancies,
                         total_applications=total_applications,
                         application_statuses=application_statuses,
                         test_stats=test_stats,
                         daily_applications=daily_applications,
                         conversion_stats=conversion_stats,
                         top_candidates=top_candidates)

@app.route('/admin/analytics/export')
@login_required
@role_required('admin')
def admin_export_analytics():
    """Экспорт аналитики администратора"""
    from sqlalchemy import func
    import pandas as pd
    from io import BytesIO
    
    try:
        # Создаем Excel файл с несколькими листами
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: Общая статистика
            general_stats = {
                'Метрика': ['Всего пользователей', 'Всего департаментов', 'Всего вакансий', 'Всего заявок', 'Всего тестов'],
                'Значение': [
                    User.query.count(),
                    Department.query.count(),
                    Vacancy.query.count(),
                    Application.query.count(),
                    Test.query.count()
                ]
            }
            pd.DataFrame(general_stats).to_excel(writer, sheet_name='Общая статистика', index=False)
            
            # Лист 2: Статистика заявок
            applications_data = []
            for app in Application.query.all():
                applications_data.append({
                    'ID': app.id,
                    'Кандидат': app.candidate.full_name,
                    'Вакансия': app.vacancy.title,
                    'Департамент': app.vacancy.department.name,
                    'Статус': APPLICATION_STATUSES.get(app.status, app.status),
                    'Дата подачи': app.created_at.strftime('%d.%m.%Y %H:%M'),
                    'HR решение': app.hr_decision or 'Не принято',
                    'Решение департамента': app.dept_decision or 'Не принято',
                    'Финальное решение': app.final_decision or 'Не принято'
                })
            pd.DataFrame(applications_data).to_excel(writer, sheet_name='Заявки', index=False)
            
            # Лист 3: Результаты тестов
            test_results_data = []
            for result in TestResult.query.all():
                test_results_data.append({
                    'ID теста': result.test_id,
                    'Название теста': result.test.name,
                    'Тип теста': result.test.type,
                    'Кандидат': result.application.candidate.full_name,
                    'Вакансия': result.application.vacancy.title,
                    'Результат': result.score,
                    'Максимум': result.max_score,
                    'Процент': round((result.score / result.max_score) * 100, 2) if result.max_score > 0 else 0,
                    'Дата прохождения': result.completed_at.strftime('%d.%m.%Y %H:%M')
                })
            pd.DataFrame(test_results_data).to_excel(writer, sheet_name='Результаты тестов', index=False)
            
            # Лист 4: Статистика департаментов
            dept_data = []
            for dept in Department.query.all():
                dept_data.append({
                    'Департамент': dept.name,
                    'Глава': dept.head.full_name if dept.head else 'Не назначен',
                    'Вакансий': dept.vacancies.count(),
                    'Заявок': Application.query.join(Vacancy).filter(Vacancy.department_id == dept.id).count()
                })
            pd.DataFrame(dept_data).to_excel(writer, sheet_name='Департаменты', index=False)
        
        output.seek(0)
        
        return send_file(
            BytesIO(output.getvalue()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'admin_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'error')
        return redirect(url_for('admin_analytics'))

@app.route('/hr/analytics/export')
@login_required
@role_required('hr')
def hr_export_analytics():
    """Экспорт аналитики HR"""
    import pandas as pd
    from io import BytesIO
    
    try:
        # Получаем заявки только для вакансий этого HR
        my_applications = Application.query.join(Vacancy).filter(
            Vacancy.created_by == current_user.id
        ).all()
        
        if not my_applications:
            flash('Нет данных для экспорта', 'warning')
            return redirect(url_for('hr_analytics'))
        
        # Создаем Excel файл
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист 1: Мои заявки
            applications_data = []
            for app in my_applications:
                applications_data.append({
                    'ID': app.id,
                    'Кандидат': app.candidate.full_name,
                    'Email кандидата': app.candidate.email,
                    'Вакансия': app.vacancy.title,
                    'Статус': APPLICATION_STATUSES.get(app.status, app.status),
                    'Дата подачи': app.created_at.strftime('%d.%m.%Y %H:%M'),
                    'HR решение': app.hr_decision or 'Не принято',
                    'HR заметки': app.hr_notes or '',
                    'Решение департамента': app.dept_decision or 'Не принято',
                    'Дата интервью': app.interview_date.strftime('%d.%m.%Y %H:%M') if app.interview_date else '',
                    'Финальное решение': app.final_decision or 'Не принято'
                })
            pd.DataFrame(applications_data).to_excel(writer, sheet_name='Заявки', index=False)
            
            # Лист 2: Результаты тестов
            test_results_data = []
            for app in my_applications:
                for result in TestResult.query.filter_by(application_id=app.id).all():
                    test_results_data.append({
                        'Кандидат': app.candidate.full_name,
                        'Вакансия': app.vacancy.title,
                        'Тест': result.test.name,
                        'Тип': result.test.type,
                        'Результат': result.score,
                        'Максимум': result.max_score,
                        'Процент': round((result.score / result.max_score) * 100, 2) if result.max_score > 0 else 0,
                        'Дата': result.completed_at.strftime('%d.%m.%Y %H:%M')
                    })
            
            if test_results_data:
                pd.DataFrame(test_results_data).to_excel(writer, sheet_name='Результаты тестов', index=False)
            
            # Лист 3: Мои вакансии
            vacancies_data = []
            for vacancy in Vacancy.query.filter_by(created_by=current_user.id).all():
                applications_count = vacancy.applications.count()
                approved_count = vacancy.applications.filter_by(final_decision='approved').count()
                rejected_count = vacancy.applications.filter_by(final_decision='rejected').count()
                
                vacancies_data.append({
                    'ID': vacancy.id,
                    'Название': vacancy.title,
                    'Дисциплина': vacancy.discipline,
                    'Департамент': vacancy.department.name,
                    'Тип занятости': EMPLOYMENT_TYPES.get(vacancy.employment_type, vacancy.employment_type),
                    'Заявок получено': applications_count,
                    'Одобрено': approved_count,
                    'Отклонено': rejected_count,
                    'Создана': vacancy.created_at.strftime('%d.%m.%Y'),
                    'Прием до': vacancy.application_end.strftime('%d.%m.%Y'),
                    'Активна': 'Да' if vacancy.is_active else 'Нет'
                })
            pd.DataFrame(vacancies_data).to_excel(writer, sheet_name='Вакансии', index=False)
        
        output.seek(0)
        
        return send_file(
            BytesIO(output.getvalue()),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'hr_analytics_{current_user.last_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'error')
        return redirect(url_for('hr_analytics'))

@app.route('/download_document/<path:filename>')
@login_required
def download_document(filename):
    """Безопасное скачивание документов"""
    # Проверяем права доступа - HR, администраторы, главы департаментов и владельцы заявок
    if current_user.role in ['admin', 'hr']:
        # Администраторы и HR имеют полный доступ
        pass
    elif current_user.role == 'department_head':
        # Главы департаментов могут скачивать документы заявок из своего департамента
        safe_filename = unquote(filename)
        
        # Ищем заявку с этим документом в департаменте текущего главы
        applications = Application.query.join(Vacancy).filter(
            Vacancy.department_id == current_user.department_id
        ).all()
        
        has_access = False
        for app in applications:
            all_files = []
            for field in ['diploma_files', 'degree_files', 'course_certificates', 'language_certificates', 'award_documents']:
                field_value = getattr(app, field)
                if field_value:
                    try:
                        files = json.loads(field_value)
                        # Проверяем как с подпапкой, так и без неё
                        file_paths = [f, f.split('/')[-1] if '/' in f else f]
                        all_files.extend(file_paths)
                    except:
                        pass
            
            if any(safe_filename.endswith(f) or f.endswith(safe_filename) for f in all_files):
                has_access = True
                break
        
        if not has_access:
            flash('Доступ запрещен.', 'error')
            return redirect(url_for('dept_dashboard'))
    
    elif current_user.role == 'candidate':
        # Для кандидатов проверяем, что это их документ
        safe_filename = unquote(filename)
        
        # Проверяем, что кандидат имеет право на скачивание этого документа
        applications = Application.query.filter_by(candidate_id=current_user.id).all()
        has_access = False
        
        for app in applications:
            all_files = []
            for field in ['diploma_files', 'degree_files', 'course_certificates', 'language_certificates', 'award_documents']:
                field_value = getattr(app, field)
                if field_value:
                    try:
                        files = json.loads(field_value)
                        all_files.extend(files)
                    except:
                        pass
            
            if safe_filename in all_files or any(f.endswith(safe_filename) for f in all_files):
                has_access = True
                break
        
        if not has_access:
            flash('Файл не найден или доступ запрещен.', 'error')
            return redirect(url_for('candidate_dashboard'))
    else:
        flash('Доступ запрещен.', 'error')
        return redirect(url_for('index'))
    
    try:
        upload_folder = os.path.join(current_app.root_path, 'uploads', 'documents')
        file_path = os.path.join(upload_folder, filename)
        
        # Проверяем что файл существует и находится в разрешенной директории
        if not os.path.exists(file_path) or not os.path.commonpath([upload_folder, file_path]) == upload_folder:
            flash('Файл не найден.', 'error')
            return redirect(url_for('index'))
        
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash('Ошибка при скачивании файла.', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    app.run(debug=True) 