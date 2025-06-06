import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Конфигурация Email
EMAIL_CONFIG = {
    # Режим тестирования (True - не отправлять реальные письма)
    'TESTING_MODE': os.getenv('EMAIL_TESTING_MODE', 'true').lower() == 'true',
    
    # Настройки SMTP сервера
    'SMTP_SERVER': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'SMTP_PORT': int(os.getenv('SMTP_PORT', 587)),
    'SMTP_USERNAME': os.getenv('SMTP_USERNAME', ''),
    'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD', ''),
    'SMTP_USE_TLS': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
    
    # Настройки отправителя
    'FROM_NAME': os.getenv('FROM_NAME', 'АУЭС HR Платформа'),
    'FROM_EMAIL': os.getenv('FROM_EMAIL', 'hr@aues.kz'),
}

# Предустановленные конфигурации для популярных провайдеров
SMTP_PROVIDERS = {
    'gmail': {
        'server': 'smtp.gmail.com',
        'port': 587,
        'use_tls': True,
        'description': 'Gmail (требуется пароль приложения)'
    },
    'yandex': {
        'server': 'smtp.yandex.ru',
        'port': 587,
        'use_tls': True,
        'description': 'Yandex Mail'
    },
    'mailru': {
        'server': 'smtp.mail.ru',
        'port': 587,
        'use_tls': True,
        'description': 'Mail.ru'
    },
    'outlook': {
        'server': 'smtp-mail.outlook.com',
        'port': 587,
        'use_tls': True,
        'description': 'Outlook.com'
    }
}

def get_email_config():
    """Получить конфигурацию email"""
    return EMAIL_CONFIG

def get_smtp_providers():
    """Получить список доступных SMTP провайдеров"""
    return SMTP_PROVIDERS 