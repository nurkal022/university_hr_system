#!/usr/bin/env python3

import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, '/var/www/aues')

from app import app

# Создаем экземпляр приложения
application = app

if __name__ == "__main__":
    application.run() 