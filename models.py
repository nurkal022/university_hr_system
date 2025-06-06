from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    middle_name = db.Column(db.String(80))
    role = db.Column(db.String(20), nullable=False)  # admin, hr, department_head, candidate
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    department = db.relationship('Department', foreign_keys=[department_id], backref='users')
    applications = db.relationship('Application', foreign_keys='Application.candidate_id', backref='candidate', lazy='dynamic')
    created_vacancies = db.relationship('Vacancy', foreign_keys='Vacancy.created_by', backref='created_by_user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name or ''}".strip()

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    head_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    head = db.relationship('User', foreign_keys=[head_id])
    vacancies = db.relationship('Vacancy', backref='department', lazy='dynamic')

# Создаем промежуточную таблицу для связи многие-ко-многим между вакансиями и тестами
vacancy_tests = db.Table('vacancy_tests',
    db.Column('vacancy_id', db.Integer, db.ForeignKey('vacancy.id'), primary_key=True),
    db.Column('test_id', db.Integer, db.ForeignKey('test.id'), primary_key=True)
)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # iq, eq, custom
    questions = db.Column(db.Text, nullable=False)  # JSON строка с вопросами
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    creator = db.relationship('User', foreign_keys=[created_by])
    vacancies = db.relationship('Vacancy', secondary=vacancy_tests, back_populates='required_tests')

class Vacancy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'), nullable=False)
    discipline = db.Column(db.String(200), nullable=False)
    employment_type = db.Column(db.String(50), nullable=False)  # full, part, guest
    work_format = db.Column(db.String(50), nullable=False)  # office, online, hybrid
    contract_duration = db.Column(db.String(100))
    salary = db.Column(db.String(100))
    
    # Требования
    education_level = db.Column(db.String(50), nullable=False)  # bachelor, master, phd
    required_specialty = db.Column(db.String(200))
    min_experience = db.Column(db.Integer, default=0)
    additional_skills = db.Column(db.Text)
    
    # Параметры отбора
    scientific_activity_level = db.Column(db.String(100))
    teaching_formats = db.Column(db.Text)  # JSON строка
    
    # Даты
    application_start = db.Column(db.DateTime, nullable=False)
    application_end = db.Column(db.DateTime, nullable=False)
    work_start_date = db.Column(db.DateTime)
    
    # Ответственные
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_person = db.Column(db.String(200))
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(50))
    
    # Дополнительная информация
    description = db.Column(db.Text)
    attachments = db.Column(db.Text)  # JSON строка с путями к файлам
    
    # Статус
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    required_tests = db.relationship('Test', secondary=vacancy_tests, back_populates='vacancies')
    applications = db.relationship('Application', backref='vacancy', lazy='dynamic')

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vacancy_id = db.Column(db.Integer, db.ForeignKey('vacancy.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Личная информация кандидата
    birth_date = db.Column(db.Date)
    citizenship = db.Column(db.String(100))
    city = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    marital_status = db.Column(db.String(50))
    military_status = db.Column(db.String(100))
    no_criminal_record = db.Column(db.Boolean, default=False)
    has_disability = db.Column(db.Boolean, default=False)
    is_pensioner = db.Column(db.Boolean, default=False)
    
    # Образование (JSON)
    education = db.Column(db.Text)
    
    # Опыт работы (JSON)
    work_experience = db.Column(db.Text)
    
    # Научная деятельность
    academic_degree = db.Column(db.String(100))
    academic_title = db.Column(db.String(100))
    title_date = db.Column(db.Date)
    publications_count = db.Column(db.Integer, default=0)
    key_publications = db.Column(db.Text)
    projects_count = db.Column(db.Integer, default=0)
    projects_list = db.Column(db.Text)
    h_index = db.Column(db.Integer)
    patents = db.Column(db.Text)
    
    # Курсы повышения квалификации (JSON)
    courses = db.Column(db.Text)
    
    # Языки (JSON)
    languages = db.Column(db.Text)
    
    # Награды (JSON)
    awards = db.Column(db.Text)
    
    # Документы для загрузки (JSON - пути к файлам)
    diploma_files = db.Column(db.Text)  # Дипломы
    degree_files = db.Column(db.Text)   # Документы об ученой степени
    course_certificates = db.Column(db.Text)  # Сертификаты курсов
    language_certificates = db.Column(db.Text)  # Сертификаты языков
    award_documents = db.Column(db.Text)  # Документы о наградах
    
    # Мотивационное письмо
    motivation_letter = db.Column(db.Text)
    video_presentation = db.Column(db.String(500))
    
    # Документы (JSON) - оставляем для совместимости
    documents = db.Column(db.Text)
    
    # Согласия
    data_processing_consent = db.Column(db.Boolean, default=False)
    video_audio_consent = db.Column(db.Boolean, default=False)
    
    # Статусы и процесс обработки
    status = db.Column(db.String(50), default='pending')  # pending, hr_review, revision_requested, dept_review, interview_scheduled, voting, approved, rejected
    hr_notes = db.Column(db.Text)
    hr_decision = db.Column(db.String(20))  # approve, reject, revise, request_revision
    hr_decision_date = db.Column(db.DateTime)
    
    # Доработка заявки
    revision_requested = db.Column(db.Boolean, default=False)
    revision_notes = db.Column(db.Text)  # Комментарии HR о необходимых доработках
    revision_requested_date = db.Column(db.DateTime)
    revision_count = db.Column(db.Integer, default=0)  # Количество раз отправлено на доработку
    
    # Решение главы департамента
    dept_decision = db.Column(db.String(20))  # recommend, reject
    dept_notes = db.Column(db.Text)
    dept_decision_date = db.Column(db.DateTime)
    reviewed_by_dept_head = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Интервью
    interview_date = db.Column(db.DateTime)
    interview_format = db.Column(db.String(50))  # online, offline
    interview_link = db.Column(db.String(500))
    interview_address = db.Column(db.String(500))
    
    # Финальное решение
    final_decision = db.Column(db.String(20))  # approved, rejected
    final_notes = db.Column(db.Text)
    contract_duration_offered = db.Column(db.String(50))
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    dept_reviewer = db.relationship('User', foreign_keys=[reviewed_by_dept_head])
    votes = db.relationship('CommissionVote', backref='application', lazy='dynamic')

class CommissionVote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    voter_email = db.Column(db.String(120), nullable=False)
    voter_name = db.Column(db.String(200))
    
    # Голосование
    vote = db.Column(db.String(20))  # approve, reject - заполняется при голосовании
    justification = db.Column(db.Text)  # заполняется при голосовании
    contract_duration = db.Column(db.String(50))  # 1-3 years
    
    # Магическая ссылка
    magic_token = db.Column(db.String(100), unique=True, nullable=False)
    token_used = db.Column(db.Boolean, default=False)
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    voted_at = db.Column(db.DateTime)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.magic_token:
            self.magic_token = str(uuid.uuid4())

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    test_type = db.Column(db.String(20), nullable=False)  # iq, eq
    answers = db.Column(db.Text)  # JSON строка с ответами
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    application = db.relationship('Application')
    test = db.relationship('Test')

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    user = db.relationship('User', foreign_keys=[user_id]) 