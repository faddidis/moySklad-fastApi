import base64
from app.core import config

# Создаем заголовки с базовой аутентификацией
def get_headers():
    # Пробуем с более стандартным подходом к токену
    return {
        "Authorization": f"Bearer {config.MS_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    } 